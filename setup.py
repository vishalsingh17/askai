from setuptools import setup  # type: ignore


setup(
    name="askai",
    version="0.1",
    py_modules=["main"],
    install_requires=[
        "click==8.1.3",
        "openai==0.25.0",
        "PyYAML==6.0",
    ],
    entry_points="""
        [console_scripts]
        askai=main:askai
    """,
)
