from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from storages.utils import clean_name
from urllib.parse import urljoin
from django.utils.encoding import force_text
from django.core.exceptions import SuspiciousOperation


def safe_join(base, *paths):
    """
    A version of django.utils._os.safe_join for S3 paths.

    Joins one or more path components to the base path component intelligently.
    Returns a normalized version of the final path.

    The final path must be located inside of the base path component (otherwise
    a ValueError is raised).

    Paths outside the base path indicate a possible security sensitive operation.
    """
    base_path = force_text(base)
    paths = map(lambda p: force_text(p), paths)
    final_path = urljoin(base_path + ("/" if not base_path.endswith("/") else ""), *paths)
    # Ensure final_path starts with base_path and that the next character after
    # the final path is '/' (or nothing, in which case final_path must be
    # equal to base_path).
    base_path_len = len(base_path) - 1
    if not final_path.startswith(base_path) \
       or final_path[base_path_len:base_path_len + 1] not in ('', '/'):
        raise ValueError('the joined path is located outside of the base path'
                         ' component')
    return final_path




class StaticStorage(S3Boto3Storage):
    location = settings.STATIC_LOCATION
    default_acl = 'public-read'


class DatabaseFileStorage(S3Boto3Storage):
    location = settings.DATABASE_FILE_LOCATION
    default_acl = 'public-read'
    file_overwrite = False


    def copy(self,from_path,to_path):
        #print(from_path,to_path)
        #from_path = clean_name(from_path)
        #to_path = clean_name(to_path)
        #print(from_path,to_path)
        #from_path = self._normalize_name(from_path)
        #to_path = self._normalize_name(to_path)
        print(from_path,to_path)
        
        copy_result = self.connection.meta.client.copy_object(
            Bucket=self.bucket_name,
            CopySource=self.bucket_name + "/" + self.location + from_path,
            Key=self.location + to_path)

    def mydelete(self,path):
        delete_result = self.connection.meta.client.delete(
            Bucket=self.bucket_name,
            Key=self.location + path
        )

