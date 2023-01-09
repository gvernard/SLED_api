from .singleobject import SingleObject
from .admin_collection import AdminCollection
from .sledgroup import SledGroup
from .lenses import Lenses
from .collection import Collection
from .confirmation_task import ConfirmationTask
from .user import Users
from .sledquery import SledQuery
from .datamodel import Instrument, Band, DataBase, Imaging, Spectrum, Catalogue
from .paper import Paper
from .persistent_message import PersistentMessage

default_app_config = 'lenses.apps.SledActstreamConfig'
