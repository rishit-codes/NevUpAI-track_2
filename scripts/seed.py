import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.database import AsyncSessionLocal
from app.models.domain import User, Session, Trade

def parse_time(t_str: str) -> datetime:
    if not t_str:
        return None
    try:
        return datetime.fromisoformat(t_str.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now(timezone.utc)

async def seed_data(filepath="nevup_seed_dataset.json"):
    if not os.path.exists(filepath):
        print(f"Seed file {filepath} not found. Skipping seed.")
        return

    with open(filepath, 'r') as f:
        data = json.load(f)

    traders_data = data.get('traders', []) if isinstance(data, dict) else data

    async with AsyncSessionLocal() as db:
        for trader in traders_data:
            user_id = trader.get('userId')
            if not user_id: continue
            
            try:
                u_uuid = uuid.UUID(user_id)
            except ValueError:
                print(f"Invalid UUID for user {user_id}")
                continue

            # Upsert User
            result = await db.execute(select(User).where(User.user_id == u_uuid))
            user = result.scalar_one_or_none()
            if not user:
                user = User(user_id=u_uuid, name=trader.get('name'))
                db.add(user)
                await db.commit()

            sessions = trader.get('sessions', [])
            for session in sessions:
                session_id = session.get('sessionId') or session.get('session_id')
                if not session_id: continue
                s_uuid = uuid.UUID(session_id)
                
                result = await db.execute(select(Session).where(Session.session_id == s_uuid))
                s = result.scalar_one_or_none()
                if not s:
                    s_date = session.get('date')
                    s = Session(
                        session_id=s_uuid,
                        user_id=u_uuid,
                        started_at=parse_time(s_date),
                        ended_at=parse_time(s_date),
                        trade_count=session.get('tradeCount', 0),
                        win_rate=session.get('winRate'),
                        total_pnl=session.get('totalPnl')
                    )
                    db.add(s)
                    await db.commit()
                    
                trades = session.get('trades', [])
                for trade in trades:
                    trade_id = trade.get('tradeId') or trade.get('trade_id')
                    if not trade_id: continue
                    t_uuid = uuid.UUID(trade_id)
                    
                    result = await db.execute(select(Trade).where(Trade.trade_id == t_uuid))
                    t = result.scalar_one_or_none()
                    if not t:
                        t = Trade(
                            trade_id=t_uuid,
                            session_id=s_uuid,
                            user_id=u_uuid,
                            asset=trade.get('asset', 'UNKNOWN'),
                            asset_class=trade.get('assetClass', 'UNKNOWN'),
                            direction=trade.get('direction', 'UNKNOWN'),
                            entry_price=trade.get('entryPrice', 0.0),
                            exit_price=trade.get('exitPrice'),
                            quantity=trade.get('quantity', 0.0),
                            entry_at=parse_time(trade.get('entryAt')),
                            exit_at=parse_time(trade.get('exitAt')),
                            status=trade.get('status', 'CLOSED'),
                            outcome=trade.get('outcome'),
                            pnl=trade.get('pnl'),
                            plan_adherence=trade.get('planAdherence'),
                            emotional_state=trade.get('emotionalState'),
                            entry_rationale=trade.get('entryRationale'),
                            revenge_flag=trade.get('revengeFlag', False)
                        )
                        db.add(t)
                        await db.commit()

        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
