from django import template

register = template.Library()


@register.simple_tag
def greeting(name):
    return f'Hello {name}'


@register.filter
def shout(value):
    return value.upper()


def unused_tag(value):
    return value
