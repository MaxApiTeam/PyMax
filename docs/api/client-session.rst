Session storage
===============

.. currentmodule:: pymax.session

``Client`` и ``WebClient`` используют этот контракт для token,
device/user-agent и sync-state. Выбор и lifecycle хранилища описаны в разделе
:ref:`client-session-guide`.

.. autoclass:: SessionInfo
   :members:

.. autoclass:: StoreProtocol
   :members:

.. autoclass:: SessionStore
   :members:

.. autoclass:: InMemoryStore
   :members:
