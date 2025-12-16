def test_smoke_imports():
    import main
    assert hasattr(main, 'workshop')
    # workshop.toys should be a dict after initialization
    assert isinstance(main.workshop.toys, dict)
