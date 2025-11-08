Color Transfer Framework Documentation
=======================================

Welcome to the Color Transfer Framework v2.0 documentation!

The Color Transfer Framework is a production-ready Python framework for transferring
colors between images using various algorithms and color spaces.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api/index
   guides/index
   examples/index

Features
--------

* **Multiple Algorithms**: Reinhard (LAB, LCH, RGB), Histogram Matching, RGB Direct
* **5 Interfaces**: REST API, Web UI, Enhanced Web UI, CLI, TUI
* **Production Ready**: Docker deployment, CI/CD, monitoring, comprehensive testing
* **High Performance**: Redis caching, Celery async processing, optional GPU support
* **Secure**: Input validation, rate limiting, security headers, CORS
* **Well Tested**: 88% coverage, 6 test types (unit, integration, load, visual, contract, mutation)
* **Observable**: Prometheus metrics, Grafana dashboards, distributed tracing

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Install from source
   git clone https://github.com/mgdavisxvs/ColorTransfer.git
   cd ColorTransfer
   pip install -e .

   # Or with Docker
   docker-compose up -d

Basic Usage
~~~~~~~~~~~

Python API:

.. code-block:: python

   from color_transfer_framework import TransferEngine
   import cv2

   # Load images
   source = cv2.imread('source.jpg')
   target = cv2.imread('target.jpg')

   # Transfer colors
   engine = TransferEngine()
   result = engine.transfer(source, target, algorithm='reinhard_lab')

   # Save result
   cv2.imwrite('result.jpg', result)

REST API:

.. code-block:: bash

   # Start API server
   docker-compose up -d api

   # Transfer colors
   curl -X POST http://localhost:8000/api/v1/transfer \
     -F "source_image=@source.jpg" \
     -F "target_image=@target.jpg" \
     -F "algorithm=reinhard_lab"

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
