from setuptools import find_packages, setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="openmanus",
    version="0.4.0",
    author="mannaandpoem and OpenManus Team",
    author_email="mannaandpoem@gmail.com",
    description="A versatile agent that can solve various tasks using multiple tools and an operational platform control plane",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FoundationAgents/OpenManus",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.13.4,<3",
        "openai>=1.58.1,<1.67.0",
        "tenacity~=9.0.0",
        "pyyaml~=6.0.2",
        "loguru~=0.7.3",
        "structlog>=24.1.0,<26.0.0",
        "numpy",
        "datasets>=3.2,<3.5",
        "html2text~=2024.2.26",
        "gymnasium>=1.0,<1.2",
        "pillow>=10.4,<11",
        "browsergym~=0.13.3",
        "uvicorn~=0.34.0",
        "unidiff~=0.7.5",
        "uv>=0.6.0",
        "googlesearch-python~=1.3.0",
        "aiofiles~=24.1.0",
        "colorama~=0.4.6",
        "SQLAlchemy>=2.0,<3",
        "asyncpg>=0.29,<1",
        "aiosqlite>=0.20,<1",
        "Alembic>=1.14,<2",
        "PyJWT>=2.8,<3",
        "pwdlib[argon2]>=0.2,<1",
        "redis>=5,<7",
        "boto3~=1.37.18",
        "daytona==0.210.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    entry_points={
        "console_scripts": [
            "openmanus=main:main",
        ],
    },
)