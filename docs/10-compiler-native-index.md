# Compiler-native index before a generic code graph

슈퍼루프 firmware의 첫 구조 인덱스는 실제 build command에서 출발한다. 소스 트리만 파싱하면
제품 variant마다 달라지는 define, include path, generated header, toolchain option을 잃을 수
있다.

## 우선순위

1. variant별 `compile_commands.json`
2. compiler가 생성한 `.d` include dependency
3. linker map과 symbol/section report
4. clangd, clang tooling, ctags/cscope 같은 read-only query layer
5. 필요성이 실측된 뒤 선택형 knowledge graph

Clang compilation database는 translation unit마다 작업 디렉터리와 실제 compile arguments를
기록하며, 같은 source가 여러 configuration으로 컴파일되는 경우 여러 command object를 가질
수 있다. 따라서 variant ID와 database hash를 함께 보존해야 한다.
[Clang JSON Compilation Database](https://clang.llvm.org/docs/JSONCompilationDatabase.html)

GCC의 `-MD`/`-MMD`는 compile 과정에서 dependency 파일을 생성하고 `-MF`는 출력 위치를
지정한다. `-MMD`는 system header를 제외하므로 분석 목적에 따라 `-MD`와 구분해야 한다.
[GCC preprocessor options](https://gcc.gnu.org/onlinedocs/gcc/Preprocessor-Options.html)

GNU linker map은 예를 들어 `-Wl,-Map=output.map`으로 생성할 수 있다. toolchain마다 syntax와
내용이 다르므로 repository가 임의 flag를 주입하지 않고 승인된 build wrapper가 생성하도록
한다. [GCC link options](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html)

## 기록해야 할 provenance

```yaml
index_id: build-debug-board-c
source_commit: <40-hex>
build_variant: debug-board-c
toolchain_id: arm-none-eabi-gcc
toolchain_version: <exact-version>
compile_commands_sha256: <64-hex>
dependency_bundle_sha256: <64-hex>
linker_map_sha256: <64-hex>
generated_at_utc: <timestamp>
```

index가 source commit, variant, toolchain과 일치하지 않으면 구조 질의 결과는 stale이다.

## 슈퍼루프에서 답할 수 있는 질문

- 현재 variant에 포함되는 translation unit과 header는 무엇인가
- 변경된 header가 어떤 object 재빌드를 유발하는가
- symbol이 어느 object/section에 배치됐는가
- 정적 메모리 크기가 이전 known-good와 어떻게 달라졌는가

다음 질문은 compiler index만으로 확정하지 않는다.

- 특정 callback이 runtime에 실제 선택됐는가
- ISR과 main loop의 실제 시간 순서
- task의 WCET와 loop deadline miss
- volatile flag의 실제 producer-consumer timing

이 영역은 TRACE32, GPIO timing, coverage, UART timestamp 같은 runtime evidence가 필요하다.
