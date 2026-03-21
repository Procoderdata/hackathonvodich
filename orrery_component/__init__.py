import streamlit.components.v1 as components
import os

_RELEASE = True  # Đặt True nếu đã build, False nếu đang dev

if not _RELEASE:
    _orrery_component_func = components.declare_component(
        "orrery_component",
        url="http://localhost:5173",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/dist")
    _orrery_component_func = components.declare_component(
        "orrery_component", 
        path=build_dir
    )

def st_orrery(key=None, data=None):
    return _orrery_component_func(key=key, data=data, default=0)

__all__ = ['st_orrery']