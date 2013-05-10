# -*- coding: utf-8 -*-

from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length = 254, label = 'Username:')
    password = forms.CharField(max_length = 30, widget = forms.PasswordInput(), label = 'Password:')
    remember = forms.BooleanField(required = False, label = 'Remember Me')
