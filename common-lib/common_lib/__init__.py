from typing import Annotated

from .rmq import RMQClient

RMQClientDep = Annotated[RMQClient, RMQClient.dep()]
