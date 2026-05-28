"use client"
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import React, { memo, useMemo } from 'react'

type Props = {
    columns: { key: string, title: string, fitler_type?: "text" | "number" | "select" | "date" }[],
    data: Record<string, any>[]
}

const table = ({columns, data}: Props) => {
    const searchParams = useSearchParams();

    const { sort, order } = useMemo(() => {
        const sort = searchParams.get("sort");
        const order = searchParams.get("order");
        return {sort, order};
    },[searchParams])

  return (
    <table>
        <thead className='sticky top-0'>
            <tr>
                {columns.map((column) => (
                    <th key={column.key} className='flex flex-row gap-4'>
                        <div>
                            {column.title}
                        </div>
                        <div>
                            <div className='flex flex-col'>
                                <ChevronUp className={sort === column.key && order=="asc" ? "text-negtive" : ""} />
                                <ChevronDown className={sort === column.key && order=="desc" ? "text-negtive" : ""} />
                            </div>
                        </div>
                    </th>
                ))}
            </tr>
        </thead>
        <tbody>
            {data.map((row) => (
                <tr key={row.id}>
                    {columns.map((column) => (
                        <td key={column.key}>{row[column.key]}</td>
                    ))}
                </tr>
            ))}
        </tbody>
    </table>
  )
}

export default memo(table)