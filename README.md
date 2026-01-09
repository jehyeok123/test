# Block Diagram Generator

`diagram.py`는 `input.txt`와 `connections.txt`를 읽어 디지털 회로 블록 다이어그램을 생성합니다.
Tkinter 창에서 블록을 드래그하면 연결선도 함께 이동합니다.

## 사용 방법

```bash
python diagram.py input.txt connections.txt diagram.png
```

기본값:
- 블록 정의: `input.txt`
- 연결 정의: `connections.txt`
- 출력 이미지: `diagram.png`

PNG 저장을 위해서는 Pillow가 필요합니다.
Pillow가 없으면 PostScript(`diagram.ps`)만 생성됩니다.

## 블록 정의 (input.txt)

```ini
[BlockA]
in = a_in
out = a_out
```

## 연결 정의 (connections.txt)

```text
BlockA.a_out -> BlockB.b_in
AND Gate1: BlockA.a_out, BlockB.b_out -> BlockC.c_in
OR Gate2: BlockA.a_out, BlockB.b_out -> BlockC.c_in
MUX Gate3: BlockA.a_out, BlockB.b_out -> BlockC.c_in
```

연결에 사용되지 않은 포트가 있으면 `error.log`에 기록됩니다.
