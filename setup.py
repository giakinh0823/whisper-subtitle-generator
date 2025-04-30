from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="whisper-subtitle-generator",
    version="1.0.0",
    author="Ha Gia Kinh",
    author_email="giakinh2000@gmail.com",
    description="A GUI application for generating subtitles from videos using OpenAI's Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/giakinh0823/whisper-subtitle-generator",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "whisper_subtitle_generator": ["resources/icons/*.png", "resources/styles/*.json"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai-whisper>=20230314",
        "torch>=2.0.0",
        "tqdm>=4.64.0",
        "numpy>=1.20.0",
        "PyAudio>=0.2.11",
    ],
    entry_points={
        "console_scripts": [
            "whisper-subtitle-generator=whisper_subtitle_generator.gui:main",
        ],
    },
)