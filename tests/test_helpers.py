from east.helper_functions import clean_up_extra_args


def test_clean_up_extra_args():
    """Test that arguments are correctly cleaned up and concatenated.

    If arg is "-DXXX=yyy:
        If yyy has quotes, they must be escaped.
        If yyy has no quotes, do nothing.
    If arg is something else, add quotes around it if it contains spaces.
    """
    args = [
        "-DCONFIG_1=1000",
        "-DCONFIG_2=y",
        '-DCONFIG_3="quoted string"',
        '"quotes"',
        "arg with spaces",
    ]

    expected = '-DCONFIG_1=1000 -DCONFIG_2=y -DCONFIG_3=\\"quoted string\\" "quotes" "arg with spaces"'

    cleaned_args = clean_up_extra_args(args)

    assert cleaned_args == expected
