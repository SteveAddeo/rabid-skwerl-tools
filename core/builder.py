# Maya
import pymel.core as pm

# Skwerl
from jnts import primary


def build_rig():
    if pm.ls("guides_grp"):
        pm.error("No guides in scene")
    for guides in pm.listRelatives("guides_grp", c=1):
        name = str(guides).split("_")[0]
        prime = primary.Build(name)


