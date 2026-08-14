export const playerNames = [
  'Aarav',
  'Diya',
  'Vivaan',
  'Anaya',
  'Arjun',
  'Ishaan',
  'Kiara',
  'Rohan',
  'Meera',
  'Kabir',
  'Sara',
  'Aditya',
  'Navya',
  'Dev',
  'Riya',
  'Zara',
]

export const teamColorPresets = [
  { name: 'Emerald', fg: '#34d399', bg: 'rgba(16, 185, 129, 0.15)' },
  { name: 'Sky', fg: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)' },
  { name: 'Amber', fg: '#fbbf24', bg: 'rgba(245, 158, 11, 0.15)' },
  { name: 'Rose', fg: '#fb7185', bg: 'rgba(244, 63, 94, 0.15)' },
  { name: 'Violet', fg: '#a78bfa', bg: 'rgba(139, 92, 246, 0.15)' },
]

export const mockGame = {
  roomId: '7K3M9Q',
  code: '7K3M9Q',
  hostId: 'p-host',
  teams: {
    A: {
      id: 'A',
      name: 'Team Emerald',
      color: teamColorPresets[0],
      captainId: 'p-host',
      players: [
        { id: 'p-host', name: 'Aarav', role: 'captain' },
        { id: 'p-a2', name: 'Diya' },
      ],
    },
    B: {
      id: 'B',
      name: 'Team Sky',
      color: teamColorPresets[1],
      captainId: 'p-guest',
      players: [
        { id: 'p-guest', name: 'Rohan', role: 'captain' },
        { id: 'p-b2', name: 'Meera' },
      ],
    },
  },
  me: { id: 'p-host', name: 'Aarav', teamId: 'A' },
  battingTeamId: 'A',
  battingOrder: {
    A: ['p-host', 'p-a2'],
    B: ['p-guest', 'p-b2'],
  },
  overs: 2,
  ballsPerOver: 6,
}

export function pickName(exclude = []) {
  const pool = playerNames.filter((n) => !exclude.includes(n))
  return pool[Math.floor(Math.random() * pool.length)] ?? `Player ${Math.floor(Math.random() * 100)}`
}
