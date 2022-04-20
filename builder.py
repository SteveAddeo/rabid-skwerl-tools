# Maya
import pymel.core as pm

# Skwerl
from jnts import primary


def build_rig():
    if "guides_grp" not in pm.ls():
        pm.error("No guides in scene")
    for guides in pm.listRelatives("guides_grp", c=1):
        name = str(guides).split("_")[0]
        builder = primary.Builder(name)


