"use client"
import adminStore from '@/store/admin-store'
import Api from '@/utils/api/api'
import { useRouter } from 'next/navigation'
import React, { useEffect } from 'react'

type Props = {}

const VerifyAdmin = (props: Props) => {
    const router = useRouter();
    const setAdmin = adminStore(s => s.setAdmin);

    useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token')
      if (!token) return;

      try {
        const response = await Api.get("/user/verify")
        if (response.status === 200) {
          setAdmin(true,token)
        } else {
          setAdmin(false);
        }
      } catch (error) {
        console.log("error: ",error);
      }
    }

    verifyToken()
  }, [])
  return (
    <></>
  )
}

export default VerifyAdmin