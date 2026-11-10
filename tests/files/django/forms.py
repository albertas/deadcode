from django import forms

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'category']

    def clean_title(self):
        return self.cleaned_data['title'].strip()


class UnusedForm(forms.Form):
    name = forms.CharField(max_length=100)
