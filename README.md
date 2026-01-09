# Block Diagram Generator

`diagram.py`는 `input.txt`와 `connections.txt`를 읽어 디지털 회로 블록 다이어그램을 생성합니다.
Tkinter 창에서 블록을 드래그하면 연결선도 함께 이동합니다.
연결선은 직선이며 수평/수직이 아니면 가운데를 기준으로 90도 꺾임이 자동 생성됩니다.
중앙에 생기는 세로선을 클릭 후 좌우로 드래그하면 꺾임 위치를 이동할 수 있습니다.
배선 이동 시 위치 갱신이 안정적으로 동작하도록 수정했습니다.
블록을 이동하면 꺾임 위치는 기본(중앙)으로 돌아갑니다.
AND 게이트는 캔버스에 직접 그리는 D형(직선+반원) 형태이며 내부 구분선은 없습니다.
AND 게이트의 in/out 포트는 도형 중심선을 기준으로 배치됩니다.

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
in = 2
out = 1
```

`in`, `out`에는 포트 개수를 숫자로 입력합니다. 포트 이름은 `in1`, `in2`, `out1`처럼 자동 생성됩니다.

## 연결 정의 (connections.txt)

```text
BlockA.out1 -> BlockB.in1
AND Gate1: BlockA.out1, BlockB.out1 -> BlockC.in1
OR Gate2: BlockA.a_out, BlockB.b_out -> BlockC.c_in
MUX Gate3: BlockA.a_out, BlockB.b_out -> BlockC.c_in
```

연결에 사용되지 않은 포트가 있으면 `error.log`에 기록됩니다.
