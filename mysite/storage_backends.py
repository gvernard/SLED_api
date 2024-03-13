from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = settings.STATIC_LOCATION
    default_acl = 'public-read'


class DatabaseFileStorage(S3Boto3Storage):
    location = settings.DATABASE_FILE_LOCATION
    default_acl = 'public-read'
    file_overwrite = False


    def copy(self,from_path,to_path):
        from_path = self._normalize_name(self._clean_name(from_path))
        to_path = self._normalize_name(self._clean_name(to_path))
        print(from_path,to_path)
        
        copy_result = self.connection.meta.client.copy_object(
            Bucket=self.bucket_name,
            CopySource=self.bucket_name + "/" + self.location + from_path,
            Key=self.location + to_path)
