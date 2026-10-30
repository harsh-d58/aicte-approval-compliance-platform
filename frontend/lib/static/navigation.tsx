"use client";
import NextLink from "next/link";
import {useRouter as nextRouter,useParams as nextParams,useSearchParams} from "next/navigation";
import type {ComponentProps} from "react";
import {routeMatch,staticHref} from "./routes";
export * from "next/navigation";

export default function StaticLink(props:ComponentProps<typeof NextLink>) {
  const href = typeof props.href === "string" ? staticHref(props.href) : props.href;
  return <NextLink {...props} href={href}/>;
}
export function useRouter() {
  const router=nextRouter();
  return {...router,push:(href:string,options?:Parameters<typeof router.push>[1])=>router.push(staticHref(href),options),
    replace:(href:string,options?:Parameters<typeof router.replace>[1])=>router.replace(staticHref(href),options),
    prefetch:(href:string,options?:Parameters<typeof router.prefetch>[1])=>router.prefetch(staticHref(href),options)};
}
export function useParams<T extends Record<string,string|string[]> = Record<string,string|string[]>>():T {
  const built=nextParams<T>();
  const search=useSearchParams();
  const original=search.get("__path");
  return (original ? routeMatch(original)?.params ?? built : built) as T;
}
