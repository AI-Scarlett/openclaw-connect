# -*- coding: utf-8 -*-
"""
OpenClaw Connect - 多实例协作连接器
"""

from .connect import OpenClawConnect
from .registry import NodeRegistry
from .http_client import HttpClient
from .dispatcher import TaskDispatcher

__all__ = ["OpenClawConnect", "NodeRegistry", "HttpClient", "TaskDispatcher"]
__version__ = "1.0.0"