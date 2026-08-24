Clients API
===========

.. currentmodule:: pymax

``Client`` и ``WebClient`` используют общий набор высокоуровневых методов,
но отличаются транспортом и способом авторизации:

``Client``
   TCP-клиент с SMS-авторизацией. Поддерживает mobile ``device_type``:
   ``ANDROID``, ``IOS`` и ``DESKTOP``. Для подтверждения QR-входа через
   :meth:`Client.authorize_qr_login` используйте ``ANDROID`` или ``IOS``:
   с ``DESKTOP`` этот метод не работает.

``WebClient``
   WebSocket-клиент с QR-авторизацией. В штатной конфигурации всегда
   использует ``DeviceType.WEB``; ``ExtraConfig.device_type`` на него не
   влияет.

.. toctree::
   :maxdepth: 1

   client-client
   client-web
   client-config
   client-session
   client-versions
