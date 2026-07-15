from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from collections import deque
import hashlib
from pathlib import Path
import re
from typing import Iterable


ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
TIMESTAMP_RE = re.compile(
    r"^\s*(?:\[\s*)?(?:"
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?"
    r"|\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"
    r"|\d+\.\d+"
    r")(?:\s*\]|\s+)\s*"
)
BOOT_RE = re.compile(
    r"\b(?:boot(?:ing)?|system startup)\b",
    re.IGNORECASE,
)
PRIVATE_BEGIN_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE,
)
PRIVATE_END_RE = re.compile(
    r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE,
)

SECRET_PATTERNS = (
    re.compile(
        r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"
    ),
    re.compile(
        r"(?i)([\"']?\b(?:api[_-]?key|access[_-]?token|token|password|"
        r"passwd|secret)\b[\"']?\s*[:=]\s*)"
        r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}\]]+)"
    ),
)

SEVERITY_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True)
class DetectorRule:
    rule_id: str
    severity: str
    component: str
    pattern: re.Pattern[str]
    exclusion: re.Pattern[str] | None = None


DETECTOR_RULES = (
    DetectorRule(
        "hard_fault",
        "critical",
        "cpu",
        re.compile(r"\bHardFault\b", re.IGNORECASE),
    ),
    DetectorRule(
        "bus_fault",
        "critical",
        "cpu",
        re.compile(r"\b(?:BusFault|UsageFault|MemManage)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "assertion",
        "critical",
        "firmware",
        re.compile(r"\b(?:assert(?:ion)? failed|configASSERT)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "panic_or_fatal",
        "critical",
        "firmware",
        re.compile(r"\b(?:panic|fatal error)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "stack_overflow",
        "critical",
        "rtos",
        re.compile(r"\bstack (?:overflow|smashing)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "watchdog_reset",
        "high",
        "watchdog",
        re.compile(
            r"(?:watchdog.{0,48}(?:expired|reset|timeout|triggered)"
            r"|(?:expired|reset|timeout).{0,48}watchdog)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwatchdog\b.{0,32}\b(?:initialized|enabled|configured|started|fed)\b",
            re.IGNORECASE,
        ),
    ),
    DetectorRule(
        "brownout",
        "high",
        "power",
        re.compile(r"\b(?:brownout|brown-out|undervoltage)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "out_of_memory",
        "high",
        "memory",
        re.compile(
            r"\b(?:out of memory|allocation failed|malloc failed|OOM)\b",
            re.IGNORECASE,
        ),
    ),
    DetectorRule(
        "timeout",
        "medium",
        "runtime",
        re.compile(r"\b(?:timed out|timeout expired)\b", re.IGNORECASE),
    ),
    DetectorRule(
        "explicit_failure",
        "medium",
        "runtime",
        re.compile(
            r"(?:\b(?:test failed|operation failed)\b|\berror\s*:)",
            re.IGNORECASE,
        ),
    ),
)


class InputChangedError(RuntimeError):
    pass


class InputTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class LogLine:
    source_line: int
    session_id: str
    sanitized_text: str
    canonical_text: str


@dataclass(frozen=True)
class Signal:
    rule_id: str
    severity: str
    component: str
    source_line: int
    excerpt: str


@dataclass(frozen=True)
class DetectionScan:
    signals: tuple[Signal, ...]
    counts_by_rule: tuple[tuple[str, int], ...]
    total_count: int


@dataclass(frozen=True)
class EvidenceWindow:
    start_line: int
    end_line: int


@dataclass(frozen=True)
class PreprocessResult:
    source_name: str
    source_sha256: str
    source_size_bytes: int
    lines_total: int
    redactions: int
    estimated_total_tokens: int
    estimated_selected_tokens: int
    signal_count_total: int
    signal_counts_by_rule: tuple[tuple[str, int], ...]
    signals: tuple[Signal, ...]
    windows: tuple[EvidenceWindow, ...]
    selected_lines: tuple[LogLine, ...]

    @property
    def highest_severity(self) -> str:
        if not self.signals:
            return "none"
        return max(
            (signal.severity for signal in self.signals),
            key=SEVERITY_ORDER.__getitem__,
        )

    @property
    def has_critical_pattern(self) -> bool:
        return any(signal.severity == "critical" for signal in self.signals)

    def line_map(self) -> dict[int, str]:
        return {
            line.source_line: line.sanitized_text
            for line in self.selected_lines
        }

    def deterministic_dict(self) -> dict[str, object]:
        reduction = 0.0
        if self.estimated_total_tokens:
            reduction = max(
                0.0,
                1.0
                - (
                    self.estimated_selected_tokens
                    / self.estimated_total_tokens
                ),
            )
        return {
            "source": {
                "name": self.source_name,
                "sha256": self.source_sha256,
                "size_bytes": self.source_size_bytes,
            },
            "lines_total": self.lines_total,
            "redactions": self.redactions,
            "estimated_total_tokens": self.estimated_total_tokens,
            "estimated_selected_tokens": self.estimated_selected_tokens,
            "estimated_selection_reduction": round(reduction, 6),
            "highest_severity": self.highest_severity,
            "signal_count_total": self.signal_count_total,
            "signals_included": len(self.signals),
            "signals_truncated": self.signal_count_total > len(self.signals),
            "signal_counts_by_rule": dict(self.signal_counts_by_rule),
            "signals": [asdict(signal) for signal in self.signals],
            "windows": [asdict(window) for window in self.windows],
            "selected_line_count": len(self.selected_lines),
        }

    def evidence_bundle(self) -> dict[str, object]:
        selected_numbers = {
            line.source_line for line in self.selected_lines
        }
        included_signals = sorted(
            (
                signal
                for signal in self.signals
                if signal.source_line in selected_numbers
            ),
            key=lambda signal: (
                -SEVERITY_ORDER[signal.severity],
                signal.source_line,
                signal.rule_id,
            ),
        )[:12]
        return {
            "source": {
                "name": self.source_name,
                "sha256": self.source_sha256,
            },
            "deterministic_signal_count_total": self.signal_count_total,
            "deterministic_signals_included": len(included_signals),
            "deterministic_signals": [
                asdict(signal) for signal in included_signals
            ],
            "untrusted_log_data": [
                {
                    "line_no": line.source_line,
                    "session_id": line.session_id,
                    "text": line.sanitized_text,
                }
                for line in self.selected_lines
            ],
        }


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(len(text) // 4, len(text.encode("utf-8")) // 3, 1)


def _strip_controls(text: str) -> str:
    return "".join(
        (
            char
            if (
                char == "\t"
                or (
                    ord(char) >= 32
                    and not 0x7F <= ord(char) <= 0x9F
                    and char not in {"\u2028", "\u2029"}
                )
            )
            else " "
        )
        for char in text
    )


def _redact_secrets(text: str) -> tuple[str, int]:
    redactions = 0

    def bearer_replacement(match: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return f"{match.group(1)}<REDACTED>"

    text = SECRET_PATTERNS[0].sub(bearer_replacement, text)

    def key_value_replacement(match: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return f"{match.group(1)}<REDACTED>"

    text = SECRET_PATTERNS[1].sub(key_value_replacement, text)
    return text, redactions


def _iter_physical_lines(decoded: str) -> Iterable[str]:
    start = 0
    for match in re.finditer(r"\r\n|\r|\n", decoded):
        yield decoded[start:match.start()]
        start = match.end()
    if start < len(decoded):
        yield decoded[start:]


def _sanitize_lines(decoded: str) -> tuple[list[LogLine], int]:
    result: list[LogLine] = []
    redactions = 0
    session = 1
    in_private_key = False

    for line_number, raw_line in enumerate(
        _iter_physical_lines(decoded),
        start=1,
    ):
        cleaned = _strip_controls(ANSI_RE.sub("", raw_line))

        if in_private_key or PRIVATE_BEGIN_RE.search(cleaned):
            in_private_key = not bool(PRIVATE_END_RE.search(cleaned))
            cleaned = "<REDACTED_PRIVATE_KEY_LINE>"
            redactions += 1
        else:
            cleaned, count = _redact_secrets(cleaned)
            redactions += count

        if line_number > 1 and BOOT_RE.search(cleaned):
            session += 1

        result.append(
            LogLine(
                source_line=line_number,
                session_id=f"session-{session:03d}",
                sanitized_text=cleaned,
                canonical_text=TIMESTAMP_RE.sub("", cleaned),
            )
        )

    return result, redactions


def scan_signals(
    lines: Iterable[LogLine],
    *,
    samples_per_rule: int = 32,
) -> DetectionScan:
    if samples_per_rule < 2:
        raise ValueError("samples_per_rule must be at least 2")
    first_limit = samples_per_rule // 2
    tail_limit = samples_per_rule - first_limit
    first: dict[str, list[Signal]] = {
        rule.rule_id: [] for rule in DETECTOR_RULES
    }
    tails: dict[str, deque[Signal]] = {
        rule.rule_id: deque(maxlen=tail_limit)
        for rule in DETECTOR_RULES
    }
    counts = {rule.rule_id: 0 for rule in DETECTOR_RULES}
    for line in lines:
        for rule in DETECTOR_RULES:
            if rule.exclusion and rule.exclusion.search(line.canonical_text):
                continue
            match = rule.pattern.search(line.canonical_text)
            if match:
                counts[rule.rule_id] += 1
                start = max(0, match.start() - 80)
                end = min(len(line.sanitized_text), match.end() + 160)
                signal = Signal(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    component=rule.component,
                    source_line=line.source_line,
                    excerpt=line.sanitized_text[start:end][:240],
                )
                if len(first[rule.rule_id]) < first_limit:
                    first[rule.rule_id].append(signal)
                else:
                    tails[rule.rule_id].append(signal)
    signals = [
        signal
        for rule in DETECTOR_RULES
        for signal in (
            first[rule.rule_id] + list(tails[rule.rule_id])
        )
    ]
    signals.sort(key=lambda signal: (signal.source_line, signal.rule_id))
    counts_by_rule = tuple(
        (rule.rule_id, counts[rule.rule_id])
        for rule in DETECTOR_RULES
        if counts[rule.rule_id]
    )
    return DetectionScan(
        signals=tuple(signals),
        counts_by_rule=counts_by_rule,
        total_count=sum(counts.values()),
    )


def detect_signals(lines: Iterable[LogLine]) -> list[Signal]:
    return list(scan_signals(lines).signals)


def _merge_ranges(
    ranges: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    if not ranges:
        return []
    merged: list[tuple[int, int, int]] = []
    for start, end, rank in sorted(ranges):
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end, rank))
            continue
        old_start, old_end, old_rank = merged[-1]
        merged[-1] = (old_start, max(old_end, end), max(old_rank, rank))
    return merged


def _windows_from_selected(line_numbers: list[int]) -> list[EvidenceWindow]:
    if not line_numbers:
        return []
    windows: list[EvidenceWindow] = []
    start = previous = line_numbers[0]
    for number in line_numbers[1:]:
        if number != previous + 1:
            windows.append(EvidenceWindow(start, previous))
            start = number
        previous = number
    windows.append(EvidenceWindow(start, previous))
    return windows


def _fit_line_to_token_budget(
    line: LogLine,
    *,
    remaining_tokens: int,
    preferred_excerpt: str | None = None,
) -> tuple[LogLine | None, int]:
    overhead = 8
    if remaining_tokens <= overhead:
        return None, 0

    full_cost = estimate_tokens(line.sanitized_text) + overhead
    if full_cost <= remaining_tokens:
        return line, full_cost

    marker = " <TRUNCATED>"
    source = preferred_excerpt or line.sanitized_text
    low = 0
    high = len(source)
    best = ""
    while low <= high:
        middle = (low + high) // 2
        candidate = source[:middle] + marker
        cost = estimate_tokens(candidate) + overhead
        if cost <= remaining_tokens:
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    if not best:
        return None, 0
    fitted = replace(
        line,
        sanitized_text=best,
        canonical_text=TIMESTAMP_RE.sub("", best),
    )
    return fitted, estimate_tokens(best) + overhead


def select_evidence(
    lines: list[LogLine],
    signals: list[Signal],
    *,
    before: int = 80,
    after: int = 40,
    max_windows: int = 3,
    max_lines: int = 300,
    max_estimated_tokens: int = 3000,
    no_signal_tail: int = 80,
) -> tuple[list[LogLine], list[EvidenceWindow], int]:
    if not lines:
        return [], [], 0

    if signals:
        ranges = [
            (
                max(1, signal.source_line - before),
                min(len(lines), signal.source_line + after),
                SEVERITY_ORDER[signal.severity],
            )
            for signal in signals
        ]
        merged = _merge_ranges(ranges)
        chosen = sorted(
            sorted(merged, key=lambda item: (-item[2], item[0]))[:max_windows],
            key=lambda item: item[0],
        )
        candidate_numbers = [
            number
            for start, end, _ in chosen
            for number in range(start, end + 1)
        ]
    else:
        first = max(1, len(lines) - no_signal_tail + 1)
        candidate_numbers = list(range(first, len(lines) + 1))

    by_number = {line.source_line: line for line in lines}
    signal_excerpts: dict[int, str] = {}
    if signals:
        chosen_ranges = [(start, end) for start, end, _ in chosen]
        selected_signals = [
            signal
            for signal in sorted(
                signals,
                key=lambda signal: (
                    -SEVERITY_ORDER[signal.severity],
                    signal.source_line,
                    signal.rule_id,
                ),
            )
            if any(
                start <= signal.source_line <= end
                for start, end in chosen_ranges
            )
        ]
        for signal in selected_signals:
            signal_excerpts.setdefault(signal.source_line, signal.excerpt)
        anchor_numbers = list(signal_excerpts)
    else:
        anchor_numbers = []

    ordered_numbers = list(
        dict.fromkeys(anchor_numbers + candidate_numbers)
    )
    anchor_set = set(anchor_numbers)
    remaining_anchors = len(anchor_set)
    selected: list[LogLine] = []
    token_count = 0
    for number in ordered_numbers:
        if len(selected) >= max_lines:
            break
        line = by_number[number]
        remaining_budget = max_estimated_tokens - token_count
        if number in anchor_set and remaining_anchors:
            line_budget = remaining_budget // remaining_anchors
        else:
            line_budget = remaining_budget
        fitted, line_tokens = _fit_line_to_token_budget(
            line,
            remaining_tokens=line_budget,
            preferred_excerpt=signal_excerpts.get(number),
        )
        if number in anchor_set:
            remaining_anchors -= 1
        if fitted is None:
            continue
        selected.append(fitted)
        token_count += line_tokens

    selected.sort(key=lambda line: line.source_line)
    windows = _windows_from_selected(
        [line.source_line for line in selected]
    )
    return selected, windows, token_count


def preprocess_file(
    path: Path,
    *,
    encoding: str = "utf-8",
    max_input_bytes: int = 50 * 1024 * 1024,
    max_input_lines: int = 250_000,
    before: int = 80,
    after: int = 40,
    max_windows: int = 3,
    max_lines: int = 300,
    max_estimated_tokens: int = 3000,
) -> PreprocessResult:
    path = Path(path)
    before_stat = path.stat()
    if before_stat.st_size > max_input_bytes:
        raise InputTooLargeError(
            f"Input is {before_stat.st_size} bytes; limit is {max_input_bytes}"
        )

    raw = path.read_bytes()
    after_stat = path.stat()
    if (
        before_stat.st_size != after_stat.st_size
        or before_stat.st_mtime_ns != after_stat.st_mtime_ns
        or len(raw) != before_stat.st_size
    ):
        raise InputChangedError("Input changed while it was being read")

    digest = hashlib.sha256(raw).hexdigest()
    decoded = raw.decode(encoding, errors="replace")
    decoded_line_count = (
        decoded.count("\n")
        + decoded.count("\r")
        - decoded.count("\r\n")
    )
    if decoded and not decoded.endswith(("\n", "\r")):
        decoded_line_count += 1
    if decoded_line_count > max_input_lines:
        raise InputTooLargeError(
            f"Input has {decoded_line_count} decoded lines; "
            f"limit is {max_input_lines}"
        )
    lines, redactions = _sanitize_lines(decoded)
    estimated_total_tokens = sum(
        estimate_tokens(line.sanitized_text) + 8 for line in lines
    )
    scan = scan_signals(lines)
    signals = list(scan.signals)
    selected, windows, estimated_tokens = select_evidence(
        lines,
        signals,
        before=before,
        after=after,
        max_windows=max_windows,
        max_lines=max_lines,
        max_estimated_tokens=max_estimated_tokens,
    )
    return PreprocessResult(
        source_name=path.name,
        source_sha256=digest,
        source_size_bytes=len(raw),
        lines_total=len(lines),
        redactions=redactions,
        estimated_total_tokens=estimated_total_tokens,
        estimated_selected_tokens=estimated_tokens,
        signal_count_total=scan.total_count,
        signal_counts_by_rule=scan.counts_by_rule,
        signals=tuple(signals),
        windows=tuple(windows),
        selected_lines=tuple(selected),
    )
