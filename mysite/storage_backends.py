from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from storages.utils import clean_name
from urllib.parse import urljoin
from django.utils.encoding import force_text
from django.core.exceptions import SuspiciousOperation



class StaticStorage(S3Boto3Storage):
    location = settings.STATIC_LOCATION
    default_acl = 'public-read'


class DatabaseFileStorage(S3Boto3Storage):
    location = settings.DATABASE_FILE_LOCATION
    default_acl = 'public-read'
    #file_overwrite = False # This adds extra random characters to the file name


    def copy(self,from_path,to_path):
        copy_result = self.connection.meta.client.copy_object(
            Bucket=self.bucket_name,
            CopySource=self.bucket_name + "/" + self.location + from_path,
            Key=self.location + to_path)


    def mydelete(self,path):
        delete_result = self.connection.meta.client.delete_object(
            Bucket=self.bucket_name,
            Key=self.location + path
        )

