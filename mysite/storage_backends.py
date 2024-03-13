from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'


class DatabaseFileStorage(S3Boto3Storage):
    location = 'files'
    default_acl = 'public-read'
    file_overwrite = False


    def rename(self,new_name):
        print(new_name)
        #from_path = self._normalize_name(self._clean_name(from_path))
        #to_path = self._normalize_name(self._clean_name(to_path))

        #copy_result = self.connection.meta.client.copy_object(
        #    Bucket=self.bucket_name,
        #    CopySource=self.bucket_name + "/" + from_path,
        #    Key=to_path)

        #if copy_result['ResponseMetadata']['HTTPStatusCode'] == 200:
        #    True
        #else:
        #    False
