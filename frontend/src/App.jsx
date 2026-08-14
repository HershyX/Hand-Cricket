import { GameProvider, useGame, SCREENS } from './state/GameContext'
import Landing from './screens/Landing'
import CreateRoom from './screens/CreateRoom'
import JoinRoom from './screens/JoinRoom'
import Lobby from './screens/Lobby'
import Toss from './screens/Toss'
import TossDecision from './screens/TossDecision'
import Gameplay from './screens/Gameplay'
import InningsBreak from './screens/InningsBreak'
import Result from './screens/Result'

function Router() {
  const { screen } = useGame()

  switch (screen) {
    case SCREENS.createRoom:
      return <CreateRoom />
    case SCREENS.joinRoom:
      return <JoinRoom />
    case SCREENS.lobby:
      return <Lobby />
    case SCREENS.toss:
      return <Toss />
    case SCREENS.tossDecision:
      return <TossDecision />
    case SCREENS.gameplay:
      return <Gameplay />
    case SCREENS.inningsBreak:
      return <InningsBreak />
    case SCREENS.result:
      return <Result />
    case SCREENS.landing:
    default:
      return <Landing />
  }
}

function App() {
  return (
    <GameProvider>
      <Router />
    </GameProvider>
  )
}

export default App
