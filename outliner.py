import pymel.core as pm


LTCOLOR = [0.0, 0.40000009536743164, 1.0]
CTCOLOR = [0.0, 1.0, 0.0]
RTCOLOR = [1.0, 0.0, 0.0]


class UI(object):
    def __init__(self):
        # Check for open window
        if pm.window("outlinerColorChanger", ex=1):
            pm.deleteUI("outlinerColorChanger")
        # Window
        self.win = pm.window(
            "outlinerColorChanger", t="Outliner Color Changer v2.0", w=200, h=60, mnb=0, mxb=0)
        self.mainLayout = pm.formLayout(nd=100)
        # Color Slder
        self.colorSlider = pm.colorSliderGrp(
            "colorSlider", label="Outliner Color", rgb=(1, 0, 0), cal=(1, "left"), h=20)
        # Buttons
        self.applyBtn = pm.button(label="APPLY", command=(
            lambda *args: self.change_outline_color(pm.colorSliderGrp(self.colorSlider, q=1, rgbValue=1))))
        self.leftBtn = pm.button(label="LEFT", command=(
            lambda *args: self.change_outline_color(LTCOLOR)))
        self.centerBtn = pm.button(label="CENTER", command=(
            lambda *args: self.change_outline_color(CTCOLOR)))
        self.rightBtn = pm.button(label="RIGHT", command=(
            lambda *args: self.change_outline_color(RTCOLOR)))
        # Separator
        self.separator01 = pm.separator(h=5)
        # Layout
        self.setLayout = pm.formLayout(self.mainLayout, e=1,
                                       attachForm=[(self.colorSlider, "top", 10), (self.colorSlider, "left", 10), (self.colorSlider, "right", 10),
                                                   (self.leftBtn, "bottom", 10), (self.centerBtn,
                                                                                  "bottom", 10), (self.rightBtn, "bottom", 10)
                                                   ],
                                       attachControl=[(self.applyBtn, "top", 10, self.colorSlider),
                                                      (self.separator01, "top",
                                                       10, self.applyBtn),
                                                      ],
                                       attachPosition=[(self.applyBtn, "left", 0, 5), (self.applyBtn, "right", 0, 95),
                                                       (self.leftBtn, "left", 0,
                                                        5), (self.leftBtn, "right", 0, 31),
                                                       (self.centerBtn, "left", 0,
                                                        37), (self.centerBtn, "right", 0, 63),
                                                       (self.rightBtn, "left", 0,
                                                        69), (self.rightBtn, "right", 0, 95),
                                                       ]
                                       )

    def change_outline_color(self, color):
        """
        Changes the outline color of the selected items to given color

        Args:
            color(list): color outliner items are being changed to
        """
        nodes = pm.ls(sl=1, tr=1)
        if not nodes:
            raise RuntimeError("nothing selected")
        else:
            for node in nodes:
                pm.setAttr("{}.useOutlinerColor".format(node), True)
                pm.setAttr("{}.outlinerColor".format(node),
                           color[0], color[1], color[2], type='double3')
            pm.select(nodes, r=1)
