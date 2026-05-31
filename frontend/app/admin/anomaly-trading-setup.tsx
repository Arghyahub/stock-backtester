"use client"
import { SECTORAL_INDICES } from '@/constants/market-constants'
import React, { memo, useEffect, useState } from "react";
import DataTable, { DataTableColumnConfig } from "@/components/table/table";
import { Button } from "@/components/ui/button";
import Api from "@/utils/api/api";
import { toast } from "sonner";

type SectoralIndexType = (typeof SECTORAL_INDICES)[number] & {
  equity_id?: number;
  start_date?: string;
  end_date?: string;
  signals?: number;
};

const TableHeader: DataTableColumnConfig<SectoralIndexType>[] = [
  { key: "name", title: "Name", filter_type: "text" },
  { key: "ticker", title: "Ticker(Yahoo)", filter_type: "text" },
  { key: "start_date", title: "Start Date", filter_type: "date" },
  { key: "end_date", title: "End Date", filter_type: "date" },
  { key: "signals", title: "Signals", filter_type: "number" },
];

const AnomalyTradingSetup = () => {
  const [sectoralIndex, setSectoralIndex] =
    useState<SectoralIndexType[]>(SECTORAL_INDICES);

  const getSectoralIndices = async () => {
    try {
      const resp = await Api.get("/equity/sectoral-indices");
      if (resp.ok) {
        const data = resp?.equity as {
          equity_id: number;
          start_date: string;
          end_date: string;
          ticker: string;
          signals: number;
        }[];
        const updatedData = SECTORAL_INDICES.map((strat) => {
          const equity = data.find((eq) => eq.ticker === strat.ticker);
          if (equity) {
            return {
              ...strat,
              equity_id: equity.equity_id,
              start_date: equity.start_date,
              end_date: equity.end_date,
              signals: equity.signals,
            };
          }
          return strat;
        });
        setSectoralIndex(updatedData);
      } else {
        toast.error("Failed to fetch sectoral indices");
      }
    } catch (error) {
      toast.error("Failed to fetch sectoral indices");
    }
  };

  const trackSectoralIndices = async () => {
    try {
      const resp = await Api.post("/equity/track-equities", {
        equities: SECTORAL_INDICES,
        type: "SECTOR",
        interval: "ONE_DAY",
      });
      if (resp.ok) {
        toast.success("Sectoral indices tracked successfully");
        getSectoralIndices();
      } else {
        toast.error("Failed to track sectoral indices");
      }
    } catch (error) {
      toast.error("Failed to track sectoral indices");
    }
  };

  useEffect(() => {
    getSectoralIndices();
  }, []);

  return (
    <div className="border px-4 py-2 rounded-md flex flex-col gap-4">
      <h1 className="text-lg font-bold">Anomaly Trading Setup</h1>
      <div className="flex flex-col gap-2">
        {/* {sectoralIndex.map((strat) => (
					<div key={strat.ticker} className="flex flex-row gap-2">
						<p>{strat.name}</p>
						<p>{strat.ticker}</p>
					</div>
				))} */}
        <DataTable
          columns={TableHeader}
          data={sectoralIndex}
          HeaderComponent={
            <div className="flex flex-row gap-4">
              <Button
                onClick={trackSectoralIndices}
                size="sm"
                variant="secondary"
              >
                Re-Track All
              </Button>
              <Button size="sm" variant="destructive">
                Un-Track All
              </Button>
              <Button size="sm" variant="secondary">
                Compute Signals
              </Button>
            </div>
          }
        />
      </div>
    </div>
  );
};

export default memo(AnomalyTradingSetup)