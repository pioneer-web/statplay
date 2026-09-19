import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self,email,password=None,**extra):
        if not email: raise ValueError('E-mail obrigatório')
        email=self.normalize_email(email)
        user=self.model(email=email,**extra); user.set_password(password); user.save(using=self._db); return user
    def create_superuser(self,email,password=None,**extra):
        extra.setdefault('is_staff',True); extra.setdefault('is_superuser',True); extra.setdefault('is_active',True)
        return self.create_user(email,password,**extra)

class User(AbstractBaseUser, PermissionsMixin):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    email=models.EmailField(unique=True)
    name=models.CharField(max_length=150)
    phone=models.CharField(max_length=30,blank=True)
    is_active=models.BooleanField(default=True)
    is_staff=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    objects=UserManager(); USERNAME_FIELD='email'; REQUIRED_FIELDS=[]
    def __str__(self): return self.email
