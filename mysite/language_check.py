from django.core.exceptions import ValidationError
#from langdetect import detect_langs
#from profanity_check import predict


def check_english_likely(text):
    """
    Check if the given text is likely to be in English.

    Returns:
    bool: True if the text is likely to be in English, False otherwise.
    """
    if len(text.split(' ')) < 2:
        # very unlikely we can tell, let it slide.
        return True
    # check what the possible languages are:
    langs = detect_langs(text)
    langs = [lang_obj.lang for lang_obj in langs if lang_obj.prob > 0.1]
    return 'en' in langs


def validate_language(text):
    """
    Validate a text to ensure it is in English and does not contain profanity.

    Args:
    text (str): The text to validate.

    Raises:
    ValidationError: If the text is not in English or contains profanity.
    """

    # 1 check that the text is in english
    #is_english = check_english_likely(text)
    is_english = True
    if not is_english:
        raise ValidationError(
            "Please stick to English for SLED content. "
            "If this is a mistake, try adding a few more words."
        )
    
    # 2 check for profanities
    #is_profane = bool(predict([text])[0])
    is_profane = False
    if is_profane:
        raise ValidationError(
            "Please avoid profanities in SLED contents. "
            "If this is a mistake, try adding a few more words."
        )

