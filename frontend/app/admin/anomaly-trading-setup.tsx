"use client"
import { SECTORAL_INDICES } from '@/constants/market-constants'
import React, { memo, useEffect, useMemo, useState } from "react";
import DataTable, { DataTableColumnConfig } from "@/components/table/table";
import { Button } from "@/components/ui/button";
import Api from "@/utils/api/api";
import { toast } from "sonner";

type SectoralIndexType = (typeof SECTORAL_INDICES)[number] & {
  equity_id?: number;
  start_date?: string;
  end_date?: string;
  signal_count?: number;
  actions?: undefined;
};

const AnomalyTradingSetup = () => {
  const [sectoralIndex, setSectoralIndex] =
    useState<SectoralIndexType[]>(SECTORAL_INDICES);

  const getSectoralIndices = async () => {
    try {
      const resp = await Api.get("/equity/summary?type=SECTOR");
      console.log("resp: ", resp.ok);
      if (resp.ok) {
        const data = resp?.equities as {
          equity_id: number;
          start_date: string;
          end_date: string;
          ticker: string;
          signal_count: number;
        }[];
        const updatedData = SECTORAL_INDICES.map((strat) => {
          const equity = data.find((eq) => eq.ticker === strat.ticker);
          if (equity) {
            return {
              ...strat,
              equity_id: equity.equity_id,
              start_date: equity.start_date,
              end_date: equity.end_date,
              signal_count: equity.signal_count,
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

  const trackSectoralIndices = async (indice?: SectoralIndexType) => {
    try {
      const resp = await Api.post("/equity/track-equities", {
        equities: indice ? [indice] : SECTORAL_INDICES,
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

  const TableHeader: DataTableColumnConfig<SectoralIndexType>[] = useMemo(
    () => [
      { key: "name", title: "Name", filter_type: "text" },
      { key: "ticker", title: "Ticker(Yahoo)", filter_type: "text" },
      { key: "start_date", title: "Start Date", filter_type: "date" },
      { key: "end_date", title: "End Date", filter_type: "date" },
      { key: "signal_count", title: "Signals", filter_type: "number" },
      {
        key: "actions",
        title: "Actions",
        component: (row) => (
          <div className="flex flex-row gap-2">
            <Button
              onClick={() =>
                trackSectoralIndices({ name: row.name, ticker: row.ticker })
              }
              size="sm"
              variant="secondary"
            >
              Track
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

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
                onClick={() => trackSectoralIndices()}
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