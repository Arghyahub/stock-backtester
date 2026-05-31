"use client"

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import Config from '@/utils/config/config'
import Api from '@/utils/api/api'
import adminStore from "@/store/admin-store";
import { STRATEGIES } from "@/constants/market-constants";
import AdminLogin from "./admin-login";
import AnomalyTradingSetup from "./anomaly-trading-setup";

type MonitoredStratType = (typeof STRATEGIES)[0] & { strategy_id?: number };

export default function AdminPage() {
  const router = useRouter()
  const setAdmin = adminStore((s) => s.setAdmin);
  const is_admin = adminStore((s) => s.is_admin);
  const [MonitoredStrategies, setMonitoredStrategies] =
    useState<MonitoredStratType[]>(STRATEGIES);
  const [OpenStrategyId, setOpenStrategyId] = useState<number | null>(null);
  const [AddingStrategy, setAddingStrategy] = useState(false);
  const [IsFetchingStrategy, setIsFetchingStrategy] = useState(false);

  const handleLogout = () => {
    setAdmin(false);
  };

  const fetchStrategies = async () => {
    setIsFetchingStrategy(true);
    try {
      const res = await Api.get("/strategy");
      if (res.status === 200) {
        const dbStrategies = res.strategies as {
          strategy_id: number;
          name: string;
          key: string;
        }[];
        setMonitoredStrategies((prev) => {
          return prev.map((strat) => ({
            ...strat,
            strategy_id: dbStrategies.find((s) => s.key === strat.key)
              ?.strategy_id,
          }));
        });
      }
    } catch (error) {
      console.log("error: ", error);
    } finally {
      setIsFetchingStrategy(false);
    }
  };

  const handleAddStrategy = async (param: {
    name: string;
    description: string;
    key: string;
  }) => {
    setAddingStrategy(true);
    try {
      const res = await Api.post("/strategy", {
        name: param.name,
        description: param.description,
        key: param.key,
      });
      if (res.ok) {
        setMonitoredStrategies((prev) => {
          return prev.map((strat) => {
            if (strat.key === param.key) {
              return {
                ...strat,
                strategy_id: res.strategy_id,
              };
            }
            return strat;
          });
        });
      }
    } catch (error) {
      console.log("error: ", error);
    } finally {
      setAddingStrategy(false);
    }
  };

  useEffect(() => {
    if (!is_admin) return;
    fetchStrategies();
  }, [is_admin]);

  if (!is_admin) {
    return <AdminLogin />;
  }

  return (
    <div className="relative min-h-screen p-8 flex flex-col gap-6 w-full">
      <div className="flex flex-row justify-between">
        <div>
          <h1 className="text-2xl font-bold underline">Admin Dashboard</h1>
        </div>

        <Button variant="destructive" onClick={handleLogout}>
          Logout
        </Button>
      </div>

      <div className="flex flex-col gap-4 w-full">
        <h2 className="text-xl font-bold">Monitored Strategies</h2>
        <div className="flex flex-col gap-4 border-2 rounded-md px-4 py-2">
          {MonitoredStrategies.map((strat) => (
            <div key={strat.key} className="w-full">
              <div className="flex flex-row justify-between">
                <h3 className="text-lg font-bold">{strat.name}</h3>
                {isNaN(Number(strat.strategy_id)) ? (
                  <Button
                    onClick={() =>
                      handleAddStrategy({
                        name: strat.name,
                        description: strat.description,
                        key: strat.key,
                      })
                    }
                    disabled={AddingStrategy}
                  >
                    {IsFetchingStrategy
                      ? "Fetching..."
                      : AddingStrategy
                        ? "Adding..."
                        : "Add"}
                  </Button>
                ) : (
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenStrategyId((prev) =>
                        prev === Number(strat.strategy_id)
                          ? null
                          : Number(strat.strategy_id),
                      );
                    }}
                  >
                    Open
                  </Button>
                )}
              </div>

              <p>{strat.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col w-full h-full">
        {OpenStrategyId === 1 && <AnomalyTradingSetup />}
      </div>
    </div>
  );
}