import pytest

try:
    from .abstract_async import make_solver, send_return
except ImportError:
    from abstract_async import make_solver, send_return


@pytest.mark.asyncio
async def test_base64():
    solver = make_solver()
    body = 'A' * 60

    params = {'file': body}
    sends = {'method': 'base64', 'body': body}

    await send_return(solver, sends, solver.normal, **params)


@pytest.mark.asyncio
async def test_data_uri():
    solver = make_solver()
    body = 'A' * 60

    params = {'file': 'data:image/png;base64,' + body}
    sends = {'method': 'base64', 'body': body}

    await send_return(solver, sends, solver.normal, **params)


@pytest.mark.asyncio
async def test_invalid_file():
    solver = make_solver()
    with pytest.raises(solver.exceptions):
        await solver.normal('lost_file.png')
