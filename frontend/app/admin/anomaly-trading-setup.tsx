"use client"
import { SECTORAL_INDICES } from '@/constants/market-constants'
import React, { memo, useState } from 'react'
import DataTable, { DataTableColumnConfig } from "@/components/table/table"
import { Button } from '@/components/ui/button'

type SectoralIndexType = typeof SECTORAL_INDICES[number] & {start_date?: string, end_date?: string, index?: number}

const TableHeader:DataTableColumnConfig<SectoralIndexType>[] = [
	{key: 'name', title: 'Name', filter_type: "text"},
	{key: 'ticker', title: 'Ticker(Yahoo)', filter_type: "text"},
	{key: 'start_date', title: 'Start Date', filter_type: "date"},
	{key: 'end_date', title: 'End Date', filter_type: "date"},
	{key: 'options', title: 'Options', filter_type: "text", component: (row) => {
		return (
			<div className="flex flex-row gap-2">
				<Button size="sm" variant="secondary" onClick={() => console.log(row)}>Re-Track</Button>
				<Button size="sm" variant="destructive" onClick={() => console.log(row)}>Un-Track</Button>
			</div>
		)
	}},
]

const AnomalyTradingSetup = () => {
	const [sectoralIndex, setSectoralIndex] = useState<SectoralIndexType[]>(SECTORAL_INDICES)
	
  return (
    <div className='border px-4 py-2 rounded-md flex flex-col gap-4'>
			<h1 className='text-lg font-bold'>Anomaly Trading Setup</h1>
			<div className="flex flex-col gap-2">
				{/* {sectoralIndex.map((strat) => (
					<div key={strat.ticker} className="flex flex-row gap-2">
						<p>{strat.name}</p>
						<p>{strat.ticker}</p>
					</div>
				))} */}
				<DataTable columns={TableHeader} data={sectoralIndex} HeaderComponent={<div className='flex flex-row gap-4'>
					<Button size="sm" variant="secondary">Re-Track All</Button>
				<Button size="sm" variant="destructive">Un-Track All</Button>
				</div>} />
			</div>
    </div>
  )
}

export default memo(AnomalyTradingSetup)