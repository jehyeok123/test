# Block Diagram Generator

`diagram.py`는 `input.txt`와 `connections.txt`를 읽어 디지털 회로 블록 다이어그램을 생성합니다.
Tkinter 창에서 블록을 드래그하면 연결선도 함께 이동합니다.
연결선은 직선이며 수평/수직이 아니면 가운데를 기준으로 90도 꺾임이 자동 생성됩니다.
중앙에 생기는 세로선을 클릭 후 좌우로 드래그하면 꺾임 위치를 이동할 수 있습니다.
연결선의 가로 구간을 클릭해 위/아래로 드래그하면 해당 포트가 블록의 좌/우 면을 따라 이동합니다.
포트를 움직이면 해당 연결선의 꺾임 위치는 기본(중앙)으로 초기화됩니다.
배선 이동 시 위치 갱신이 안정적으로 동작하도록 수정했습니다.
블록을 이동하면 꺾임 위치는 기본(중앙)으로 돌아갑니다.
AND 게이트는 캔버스에 직접 그리는 D형(직선+반원) 형태이며 내부 구분선은 없습니다.
AND 게이트의 in/out 포트는 도형 중심선을 기준으로 배치됩니다.
포트 이름 텍스트는 표시하지 않으며 포트 점은 반지름 5의 검정색으로 표시됩니다.
블록 내부 색상은 연한 회색으로 표시됩니다.
블록을 더블클릭하면 테두리가 두꺼워지며, 이 상태에서 테두리를 드래그해 크기를 조절합니다.
드래그 중에 마우스를 떼는 위치까지 크기가 변경됩니다.
다시 더블클릭하면 테두리가 원래 두께로 돌아가며 크기 조절이 비활성화됩니다.
리사이즈 모드에서는 블록 이동과 포트 이동이 비활성화됩니다.
블록 이동 및 크기 조절은 10 단위로 스냅됩니다.
포트는 반지름 5의 검정색 점으로 표시됩니다.
높이를 변경해도 포트/배선의 기본 위치는 유지됩니다.
블록 폭이 바뀌면 입력 포트는 왼쪽, 출력 포트는 오른쪽에 맞춰집니다.
블록을 선택/수정하면 해당 블록과 연결된 선이 위로 올라옵니다.
세로선을 드래그해 꺾임 위치를 옮길 때는 5 단위로 스냅됩니다.
NEW 버튼에서 블록/게이트를 선택해 새 항목을 추가할 수 있습니다.
CONNECT 버튼은 포트를 빨간색으로 표시한 뒤 서로 다른 블록의 in/out 포트를 선택하면 연결선을 생성합니다.
DISCONNECT 버튼은 연결선을 빨간색으로 표시하고, 선택한 연결선을 삭제합니다.
SHOW/HIDE PORT 버튼으로 포트 점 표시를 켜거나 끌 수 있습니다.
CONNECT/DISCONNECT 모드에서는 블록 이동, 크기 조절, 포트 이동이 비활성화됩니다.

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
BlockA.out1 -> BlockB.in1 | cnt1[10:0]\ncnt2[10:0]
AND2 Gate1: BlockA.out1, BlockB.out1 -> BlockC.in1 | and_net
OR2 Gate2: BlockA.a_out, BlockB.b_out -> BlockC.c_in
MUX_2x1 Gate3: BlockA.a_out, BlockB.b_out -> BlockC.c_in
-> BlockA.in1 | cnt1\ncnt2
BlockA.out1 ->
```

연결에 사용되지 않은 포트가 있으면 `error.log`에 기록됩니다.
단일 포트 연결(`-> BlockA.in1` 또는 `BlockA.out1 ->`)은 길이 50의 가로선만 그려집니다.
포트 이동은 10 단위로 스냅됩니다.
