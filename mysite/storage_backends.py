import os
import shutil
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from storages.utils import clean_name
from urllib.parse import urljoin
from django.utils.encoding import force_text
from django.core.exceptions import SuspiciousOperation
from botocore.exceptions import ClientError
from django.core.files.storage import Storage


class StaticStorage(S3Boto3Storage):
    location = settings.STATIC_LOCATION
    default_acl = 'public-read'


class DatabaseFileStorage(S3Boto3Storage):
    location = settings.DATABASE_FILE_LOCATION + "/"
    default_acl = 'public-read'
    #file_overwrite = False # This adds extra random characters to the file name

    def _normalize_name(self, name):
        """
        Get rid of this crap: http://stackoverflow.com/questions/12535123/django-storages-and-amazon-s3-suspiciousoperation
        """
        return self.location+name

    def copy(self,from_path,to_path):
        #print(self.bucket_name + "/" + self.location + from_path,self.location + to_path)
        copy_result = self.connection.meta.client.copy_object(
            Bucket=self.bucket_name,
            CopySource=self.bucket_name + "/" + self.location + from_path,
            Key=self.location + to_path)


    def mydelete(self,fname):
        #print(self.location + fname)
        delete_result = self.connection.meta.client.delete_object(
            Bucket=self.bucket_name,
            Key=self.location + fname
        )

    def put_object(self,content,fname):
        response = self.connection.meta.client.put_object(
            Body=content,
            Bucket=self.bucket_name,
            Key=self.location + fname
        )

        


class LocalStorage(Storage):
    location = settings.MEDIA_ROOT + "/"
    file_overwrite = True
    
    def _open(self,fname,mode='rb'):
        f = open(fname,mode)
        return f

    def _save(self,fname,content):
        with open(self.location + fname,'wb') as writer:
            writer.write(content.read())
        return fname

    def path(self,fname):
        return fname

    def copy(self,from_path,to_path):
        shutil.copyfile(self.location + from_path,self.location + to_path)

    def mydelete(self,fname):
        os.remove(self.location + fname)

    def put_object(self,content,fname):
        with open(self.location + fname,'wb') as writer:
            writer.write(content)

    def exists(self,fname):
        return os.path.isfile(self.location + fname)
    
    def url(self,fname):
        return self.location + fname
