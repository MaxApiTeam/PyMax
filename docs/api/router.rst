Router API
==========

.. autoclass:: pymax.Router
   :members:
   :show-inheritance:

.. autoclass:: pymax.dispatch.ErrorScope
   :members:

.. autoclass:: pymax.dispatch.ErrorContext
   :members:

.. autodata:: pymax.ClientRouter

.. autodata:: pymax.WebRouter

Фильтры
-------

Примеры регистрации и объединения фильтров приведены в :doc:`/router`.

.. autoclass:: pymax.filters.Filter
   :exclude-members: resolve_filter_result

.. autoclass:: pymax.filters.Command

.. autoclass:: pymax.filters.Reply

.. autoclass:: pymax.filters.Forwarded

.. autoclass:: pymax.filters.FromMe

.. autoclass:: pymax.filters.HasAttachment

Middleware
----------

.. autoclass:: pymax.dispatch.Middleware

.. autodata:: pymax.dispatch.MiddlewareNext
