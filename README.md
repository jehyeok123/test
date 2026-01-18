# Block Diagram Generator

`diagram.py`는 `input.json`을 읽어 디지털 회로 블록 다이어그램을 생성합니다.
Tkinter 창에서 블록을 드래그하면 연결선도 함께 이동합니다.
연결선은 직선이며 수평/수직이 아니면 가운데를 기준으로 90도 꺾임이 자동 생성됩니다.
중앙에 생기는 세로선을 클릭 후 좌우로 드래그하면 꺾임 위치를 이동할 수 있습니다.
연결선의 가로 구간을 클릭해 위/아래로 드래그하면 해당 포트가 블록의 좌/우 면을 따라 이동합니다.
포트를 움직이면 해당 연결선의 꺾임 위치는 기본(중앙)으로 초기화됩니다.
배선 이동 시 위치 갱신이 안정적으로 동작하도록 수정했습니다.
블록을 이동하면 꺾임 위치는 기본(중앙)으로 돌아갑니다.
포트 이름 텍스트는 표시하지 않으며 포트 점은 반지름 5의 검정색으로 표시됩니다.
블록 내부 색상은 선택한 fill_color로 표시됩니다.
게이트는 `gate_image` 폴더의 이미지 파일을 사용해 표시됩니다.
블록을 더블클릭하면 테두리가 두꺼워지며, 이 상태에서 테두리를 드래그해 크기를 조절합니다.
게이트를 더블클릭하면 게이트 이미지에 두꺼운 검은 테두리가 생기며, 테두리를 드래그해 이미지 크기(서브샘플 비율)를 변경합니다.
오른쪽/위쪽 테두리를 드래그하면 게이트의 왼쪽 하단 좌표를 고정한 채 크기가 바뀌고, 왼쪽/아래쪽 테두리를 드래그하면 오른쪽 위 좌표를 고정합니다.
드래그 중에 마우스를 떼는 위치까지 크기가 변경됩니다.
다시 더블클릭하면 테두리가 원래 두께로 돌아가며 크기 조절이 비활성화됩니다.
리사이즈 모드에서는 블록 이동과 포트 이동이 비활성화됩니다.
블록 이동 및 크기 조절은 10 단위로 스냅됩니다.
포트는 반지름 5의 검정색 점으로 표시됩니다.
높이를 변경해도 포트/배선의 기본 위치는 유지됩니다.
포트는 블록의 상/하/좌/우 어느 테두리에도 생성할 수 있습니다.
게이트 포트도 블록 포트처럼 드래그로 이동할 수 있으며, 좌표는 5 단위로 스냅됩니다.
블록의 겹침 순서는 level 값에 따라 결정되며, level이 같을 때만 선택한 블록이 위로 올라옵니다.
세로선을 드래그해 꺾임 위치를 옮길 때는 5 단위로 스냅됩니다.
NEW 버튼에서 블록/게이트를 선택해 새 항목을 추가할 수 있으며, 블록은 이름만 입력하면 됩니다.
CREATE PORT 버튼은 선택한 블록의 테두리를 초록색으로 표시한 뒤, 테두리를 클릭하면 해당 위치에 포트를 추가합니다.
DELETE PORT 버튼은 선택한 블록의 포트를 빨간색으로 표시하고, 클릭한 포트를 삭제합니다.
CONNECT 버튼은 포트를 노란색으로 표시한 뒤 서로 다른 블록의 포트를 선택하면 연결선을 생성합니다.
DISCONNECT 버튼은 연결선을 빨간색으로 표시하고, 선택한 연결선을 삭제합니다.
SHOW/HIDE PORT 버튼으로 포트 점 표시를 켜거나 끌 수 있습니다.
WIRE NAME 버튼은 연결선을 파란색으로 표시하고, 선택한 연결선에 이름을 입력합니다.
BRING FRONT/SEND BACK 버튼으로 선택한 블록/게이트의 level을 이웃 level과 교환합니다.
JSON SAVE 버튼을 누르면 현재 블록/배선 정보가 `input.json`에 저장됩니다.
REMOVE 버튼을 누르면 선택한 블록/게이트와 연결된 배선을 함께 삭제합니다.
ZOOM IN/OUT 버튼으로 화면만 확대/축소합니다.
CONNECT/DISCONNECT 모드에서는 블록 이동, 크기 조절, 포트 이동이 비활성화됩니다.

## 사용 방법

```bash
python diagram.py input.json diagram.png
```

기본값:
- 입력 정의: `input.json`
- 출력 이미지: `diagram.png`

PNG 저장을 위해서는 Pillow가 필요합니다.
Pillow가 없으면 PostScript(`diagram.ps`)만 생성됩니다.

## 입력 정의 (input.json)

```json
{
  "blocks": [
    {
      "name": "BlockA",
      "kind": "BLOCK",
      "x": 80,
      "y": 80,
      "width": 160,
      "height": 100,
      "level": 0,
      "fill_color": "WHITE",
      "outline_color": "GRAY",
      "outline_enabled": true,
      "outline_thickness": 1.0,
      "outline_style": "solid",
      "font_size": 12,
      "font_family": "Arial",
      "font_weight": "bold",
      "ports": {
        "p1": {
          "side": "left",
          "offset": 0.33
        },
        "p2": {
          "side": "right",
          "offset": 0.5
        }
      }
    }
  ],
  "connections": [
    {
      "src": "BlockA.out1",
      "dst": "BlockB.in1",
      "label": "net1"
    }
  ],
  "wires": [
    {
      "src": "BlockA.out1",
      "dst": "BlockB.in1",
      "manual_mid_x": 200,
      "manual_mid_y": null
    }
  ]
}
```

블록/게이트는 `blocks`에 정의하며, `connections`는 논리 연결을 정의합니다.
`wires`에는 연결선의 꺾임 지점(`manual_mid_x`, `manual_mid_y`)과 같은 시각적 정보를 저장합니다.
포트 위치를 고정하려면 `ports` 아래에 각 포트 이름을 키로 두고 `side`, `offset`, `manual_y`를 지정합니다.
`fill_color`/`outline_color`에는 `GRAY`, `BLUE`, `RED`, `WHITE`처럼 이름 문자열을 넣으면 해당 색상이 적용됩니다.
`outline_enabled`를 false로 두면 테두리가 그려지지 않습니다.
`outline_thickness`는 0.5(Thin)/1.0(Normal)/2.0(Thick)로 저장됩니다.
`outline_style`은 `solid` 또는 `dashed`를 사용합니다.
`font_size`는 블록 이름 글꼴 크기를 의미합니다.
`font_family`는 `Arial` 또는 `Malgun Gothic`을 선택할 수 있고, `font_weight`는 `bold` 또는 `normal`입니다.
연결에 사용되지 않은 포트가 있으면 `error.log`에 기록됩니다.
포트 이동은 5 단위로 스냅됩니다.
