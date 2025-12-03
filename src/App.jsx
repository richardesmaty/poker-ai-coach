import { useEffect, useState } from "react";
import { fetchState, newHand, sendAction } from "./api";
import { Button } from "./ui/Button"; // optional UI component
import { Card, CardsRow } from "./ui/Cards"; // optional

export default function App() {
  const [game, setGame] = useState(null);

  async function loadState() {
    const data = await fetchState();
    setGame(data);
  }

  useEffect(() => {
    loadState();
  }, []);

  if (!game) return <div className="p-4">Loading table...</div>;

  const hero = game.players.find((p) => p.is_human);

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-center mb-4">Poker AI Coach</h1>

      {/* Table */}
      <div className="bg-green-800 rounded-full p-10 border-8 border-green-900 shadow-2xl">
        <div className="text-center mb-3">
          <CardsRow cards={game.community_cards} />
        </div>
        <div className="text-center text-yellow-300 text-xl font-bold">
          Pot: ${game.pot}
        </div>
      </div>

      {/* Hero Hand */}
      <div className="mt-4 text-center">
        <h2 className="text-lg mb-2">Your Hand</h2>
        <CardsRow cards={hero.hole_cards} size="large" />
      </div>

      {/* Controls */}
      <div className="mt-6 flex justify-center gap-3">
        <button
          className="px-6 py-2 bg-red-600 rounded-lg"
          onClick={async () => {
            setGame(await sendAction("fold"));
          }}
        >
          Fold
        </button>

        <button
          className="px-6 py-2 bg-blue-600 rounded-lg"
          onClick={async () => {
            setGame(await sendAction("check_call"));
          }}
        >
          Check / Call
        </button>

        <button
          className="px-6 py-2 bg-yellow-600 rounded-lg"
          onClick={async () => {
            setGame(await sendAction("bet_raise", 100));
          }}
        >
          Bet / Raise
        </button>
      </div>

      <div className="mt-4 text-center">
        <button
          className="px-4 py-2 bg-gray-700 rounded-md"
          onClick={async () => {
            setGame(await newHand());
          }}
        >
          New Hand
        </button>
      </div>
    </div>
  );
}
