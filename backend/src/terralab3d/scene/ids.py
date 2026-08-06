"""Identificadors forts per als objectes de l’escena retinguda."""
from typing import NewType

SceneEntityId = NewType("SceneEntityId", str)
SceneResourceId = NewType("SceneResourceId", str)
SceneGeneration = NewType("SceneGeneration", int)
