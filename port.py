from typing import Optional, Set, Tuple

from constants import Resource
from vertex import Vertex


class Port(Vertex):
    def __init__(self, vertex_id: Set[Tuple[int, int]], resource: Resource):
        self.resource = resource
        self.ratio = 2 if resource is not Resource.ANY else 3
        Vertex.__init__(self, vertex_id)







