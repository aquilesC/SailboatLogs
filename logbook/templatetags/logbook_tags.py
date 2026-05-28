import re
from django import template
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()

@register.filter(name='linkify_tags')
def linkify_tags(value, is_public=False):
    """
    Finds hashtags in text and converts them to HTML links pointing to the tag detail page.
    If is_public is True, it boldens them but does not link them to the internal tag page.
    """
    if not value:
        return value

    def replace_tag(match):
        tag_name = match.group(1)
        if is_public:
            return f'<strong>#{tag_name}</strong>'
        else:
            url = reverse('tag_detail', kwargs={'tag_name': tag_name.lower()})
            return f'<a href="{url}" class="text-brand-secondary hover:underline font-medium">#{tag_name}</a>'

    # Regex to find hashtags (#tag). We use \w+ to match alphanumeric characters.
    # The (#(\w+)) means we group the whole hashtag but also just the word.
    # Actually, r'#(\w+)' captures the word. Let's use a simpler approach.
    
    pattern = re.compile(r'#(\w+)')
    linked_text = pattern.sub(replace_tag, value)
    
    return mark_safe(linked_text)
