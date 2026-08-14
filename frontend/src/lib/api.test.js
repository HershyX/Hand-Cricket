import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, createRoom, joinRoom } from './api'

const ok = (body) => ({ ok: true, status: 200, json: async () => body })
const error = (status, code, message) => ({
  ok: false,
  status,
  json: async () => ({ detail: { code, message } }),
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('createRoom', () => {
  it('posts the host name and returns the room', async () => {
    const fetchMock = vi.fn(async () => ok({ room_code: 'ABC123', player_id: 'p1', room: {} }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await createRoom('Alice')
    expect(data.room_code).toBe('ABC123')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/rooms')
    expect(JSON.parse(init.body).host_name).toBe('Alice')
  })

  it('throws ApiError with the backend code on failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => error(409, 'ROOM_FULL', 'This room is full')))
    await expect(createRoom('Alice')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'ROOM_FULL',
    })
  })

  it('throws ApiError on network failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('fetch failed'))))
    await expect(createRoom('Alice')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('joinRoom', () => {
  it('posts to the room join endpoint', async () => {
    const fetchMock = vi.fn(async () => ok({ room_code: 'ABC123', player_id: 'p2', room: {} }))
    vi.stubGlobal('fetch', fetchMock)

    await joinRoom('abc123', 'Bob')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/rooms/abc123/join')
    expect(JSON.parse(init.body).player_name).toBe('Bob')
  })

  it('maps 404 room not found', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => error(404, 'ROOM_NOT_FOUND', 'Room not found')))
    await expect(joinRoom('ZZZZZZ', 'Bob')).rejects.toMatchObject({ code: 'ROOM_NOT_FOUND' })
  })

  it('maps duplicate player rejection', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => error(409, 'DUPLICATE_PLAYER', 'Name taken')))
    await expect(joinRoom('ABC123', 'Alice')).rejects.toMatchObject({ code: 'DUPLICATE_PLAYER' })
  })
})
