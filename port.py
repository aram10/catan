from typing import Optional, Set, Tuple

from constants import RESOURCE
from vertex import Vertex


class Port(Vertex):
    def __init__(self, vertex_id: Set[Tuple[int, int]], resource: RESOURCE):
        self.resource = resource
        self.ratio = (2, 1) if resource is not RESOURCE.ANY else (3, 1)
        Vertex.__init__(self, vertex_id)






