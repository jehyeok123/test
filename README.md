# Block Diagram Generator

`diagram.py`는 `input.txt`와 `connections.txt`를 읽어 디지털 회로 블록 다이어그램을 생성합니다.
Tkinter 창에서 블록을 드래그하면 연결선도 함께 이동합니다.
연결선은 직선이며 수평/수직이 아니면 가운데를 기준으로 90도 꺾임이 자동 생성됩니다.

## 사용 방법

```bash
python diagram.py input.txt connections.txt diagram.png
```

기본값:
- 블록 정의: `input.txt`
- 연결 정의: `connections.txt`
- 출력 이미지: `diagram.png`
- 게이트 심볼 정의: `gate_symbol.txt` (선택)

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

## 게이트 심볼 정의 (gate_symbol.txt)

게이트 심볼은 JSON 형식으로 정의합니다. 이미지 파일과 포트 위치를 지정하면 해당 좌표에 포트가 배치됩니다.

```json
{
  "AND": {
    "image": "and_gate.png",
    "size": [120, 80],
    "inputs": {
      "in1": [10, 25],
      "in2": [10, 55]
    },
    "outputs": {
      "out": [110, 40]
    }
  }
}
```
