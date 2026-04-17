from backend.observability import refresh_domain_gauges


def test_refresh_domain_gauges_does_not_raise_on_db_error(monkeypatch):
    class _BrokenQuery:
        def count(self):
            raise RuntimeError("db temporariamente indisponível")

    class _BrokenSession:
        def query(self, *_args, **_kwargs):
            return _BrokenQuery()

    # Não deve propagar exceção — /metrics precisa seguir disponível.
    refresh_domain_gauges(db=_BrokenSession())

