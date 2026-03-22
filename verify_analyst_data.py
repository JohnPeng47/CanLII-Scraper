"""
Verify whether the analyst comp table contains normalized numbers vs raw Edgar filings.

Approach:
- Parse the table from the image (hardcoded below)
- For each company, pull revenue/COGS/operating data from SEC Edgar XBRL API
- Compare the analyst table values to raw Edgar values
- Flag discrepancies that suggest normalization (e.g., adjusted EBITDA, stock-based comp add-backs)

Column mapping (Image -> Edgar):
  Image Column          | Edgar XBRL Concept
  --------------------- | ------------------
  2024E Revenue ($M)    | Revenues / RevenueFromContractWithCustomerExcludingAssessedTax (FY2024)
  Gross Margin (2024E)  | Derived: (Revenue - CostOfRevenue) / Revenue
  EBITDA Margin (2024E) | No direct Edgar field - analysts typically use adjusted EBITDA
  Revenue Growth 22A-23A| Derived: (Rev_FY2023 - Rev_FY2022) / Rev_FY2022
  EV/Revenue 2023A      | Ratio: Enterprise Value / Revenue_FY2023
  EV/EBITDA 2023A       | Ratio: Enterprise Value / EBITDA_FY2023

Note: EBITDA is NOT reported in GAAP filings. Analysts compute it as:
  Operating Income + D&A (+ stock-based comp adjustments in "normalized" versions)
  The difference between raw GAAP EBITDA and the analyst number reveals normalization.
"""

import json
import time
import requests
import sys
from dataclasses import dataclass

# ============================================================
# 1. PARSED TABLE DATA FROM IMAGE
# ============================================================

# Companies from "Infrastructure and Operations Management" section
# Format: (name, ticker, CIK, stock_price, market_cap_M, enterprise_value_M,
#           ev_rev_2023a, ev_ebitda_2023a, revenue_2024e_M, gross_margin_2024e,
#           ebitda_margin_2024e, fcf_margin_2024e, rev_growth_22a_23a, rev_growth_23a_24e)

COMPANIES = [
    {
        "name": "Datadog",
        "ticker": "DDOG",
        "cik": "0001561550",
        "market_cap": 44755,
        "ev": 42301,
        "ev_rev_2023a": 19.9,
        "ev_rev_2024e": 15.9,
        "ev_ebitda_2023a": None,  # N.M. in table
        "revenue_2024e": 2661,
        "gross_margin_2024e": 81.9,
        "ebitda_margin_2024e": 26.8,
        "rev_growth_22a_23a": 27.7,
        "rev_growth_23a_24e": 27.1,
    },
    {
        "name": "NetApp",
        "ticker": "NTAP",
        "cik": "0001002047",
        "market_cap": 25189,
        "ev": 24953,
        "ev_rev_2023a": 4.0,
        "ev_rev_2024e": 3.8,
        "ev_ebitda_2023a": 12.3,
        "revenue_2024e": 6536,
        "gross_margin_2024e": 71.8,
        "ebitda_margin_2024e": 31.0,
        "rev_growth_22a_23a": 21.8,
        "rev_growth_23a_24e": -0.9,  # (0.9%) in table
    },
    {
        "name": "Pure Storage",
        "ticker": "PSTG",
        "cik": "0001474432",
        "market_cap": 21696,
        "ev": 20148,
        "ev_rev_2023a": 7.1,
        "ev_rev_2024e": 6.4,
        "ev_ebitda_2023a": 30.1,
        "revenue_2024e": 3130,
        "gross_margin_2024e": 72.2,
        "ebitda_margin_2024e": 21.4,
        "rev_growth_22a_23a": 16.3,
        "rev_growth_23a_24e": 4.4,
    },
    {
        "name": "Nutanix",
        "ticker": "NTNX",
        "cik": "0001618732",
        "market_cap": 19246,
        "ev": 18741,
        "ev_rev_2023a": 9.5,
        "ev_rev_2024e": 8.2,
        "ev_ebitda_2023a": 45.1,
        "revenue_2024e": 2281,
        "gross_margin_2024e": 86.8,
        "ebitda_margin_2024e": 18.2,
        "rev_growth_22a_23a": 25.8,
        "rev_growth_23a_24e": 16.6,
    },
    {
        "name": "Dynatrace",
        "ticker": "DT",
        "cik": "0001773383",
        "market_cap": 16761,
        "ev": 15756,
        "ev_rev_2023a": 11.6,
        "ev_rev_2024e": 9.8,
        "ev_ebitda_2023a": 33.5,
        "revenue_2024e": 1615,
        "gross_margin_2024e": 84.7,
        "ebitda_margin_2024e": 29.1,
        "rev_growth_22a_23a": 24.1,
        "rev_growth_23a_24e": 23.5,
    },
    {
        "name": "Commvault Systems",
        "ticker": "CVLT",
        "cik": "0001169561",
        "market_cap": 6947,
        "ev": 6703,
        "ev_rev_2023a": 8.1,
        "ev_rev_2024e": 7.2,
        "ev_ebitda_2023a": 37.2,
        "revenue_2024e": 928,
        "gross_margin_2024e": 82.0,
        "ebitda_margin_2024e": 21.6,
        "rev_growth_22a_23a": 22.1,
        "rev_growth_23a_24e": 5.5,
    },
    {
        "name": "PagerDuty",
        "ticker": "PD",
        "cik": "0001568100",
        "market_cap": 1889,
        "ev": 1813,
        "ev_rev_2023a": 4.3,
        "ev_rev_2024e": 3.9,
        "ev_ebitda_2023a": 18.5,
        "revenue_2024e": 463,
        "gross_margin_2024e": 85.8,
        "ebitda_margin_2024e": 21.2,
        "rev_growth_22a_23a": 18.9,
        "rev_growth_23a_24e": 17.2,
    },
    # Development Tools and App Infrastructure section
    {
        "name": "Atlassian",
        "ticker": "TEAM",
        "cik": "0001650372",
        "market_cap": 66504,
        "ev": 65274,
        "ev_rev_2023a": 16.6,
        "ev_rev_2024e": 13.8,
        "ev_ebitda_2023a": None,  # N.M.
        "revenue_2024e": 4739,
        "gross_margin_2024e": 83.8,
        "ebitda_margin_2024e": 24.3,
        "rev_growth_22a_23a": 29.4,
        "rev_growth_23a_24e": 24.3,
    },
    {
        "name": "Gitlab",
        "ticker": "GTLB",
        "cik": "0001653482",
        "market_cap": 9874,
        "ev": 9003,
        "ev_rev_2023a": 15.9,
        "ev_rev_2024e": 12.2,
        "ev_ebitda_2023a": None,  # N.M.
        "revenue_2024e": 739,
        "gross_margin_2024e": 90.8,
        "ebitda_margin_2024e": 9.0,
        "rev_growth_22a_23a": 7.9,
        "rev_growth_23a_24e": 38.3,
    },
    {
        "name": "Cloudflare",
        "ticker": "NET",
        "cik": "0001477333",
        "market_cap": 32919,
        "ev": 32382,
        "ev_rev_2023a": 25.0,
        "ev_rev_2024e": 19.5,
        "ev_ebitda_2023a": None,  # N.M.
        "revenue_2024e": 1662,
        "gross_margin_2024e": 79.0,
        "ebitda_margin_2024e": 20.7,
        "rev_growth_22a_23a": 10.3,
        "rev_growth_23a_24e": 33.0,
    },
]

HEADERS = {
    "User-Agent": "AnalystDataVerifier research@example.com",
    "Accept": "application/json",
}


def fetch_company_facts(cik: str) -> dict:
    """Fetch company facts from SEC Edgar XBRL API."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def extract_annual_values(facts: dict, concept: str, namespace: str = "us-gaap") -> list:
    """
    Extract annual (10-K) values for a given XBRL concept.
    Returns list of dicts with 'end', 'val', 'fy', 'fp' keys.
    """
    try:
        units = facts["facts"][namespace][concept]["units"]
    except KeyError:
        return []

    # Try USD first, then pure (for ratios)
    for unit_key in ["USD", "pure"]:
        if unit_key in units:
            entries = units[unit_key]
            # Filter for annual filings (10-K, fp=FY)
            annual = [
                e for e in entries
                if e.get("form") in ("10-K", "10-KT")
                and e.get("fp") == "FY"
            ]
            # Deduplicate by fiscal year end date, keep latest filing
            by_end = {}
            for e in annual:
                end = e["end"]
                if end not in by_end or e.get("filed", "") > by_end[end].get("filed", ""):
                    by_end[end] = e
            return sorted(by_end.values(), key=lambda x: x["end"])
    return []


def get_revenue_concepts():
    """Return list of XBRL concepts to try for revenue, in priority order."""
    return [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "Revenue",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueServicesNet",
    ]


def get_cost_concepts():
    """Return list of XBRL concepts to try for cost of revenue."""
    return [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfServices",
    ]


def get_operating_income_concepts():
    """Return XBRL concepts for operating income."""
    return [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ]


def get_da_concepts():
    """Return XBRL concepts for depreciation & amortization."""
    return [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
        "DepreciationAmortizationAndAccretionNet",
    ]


def get_sbc_concepts():
    """Return XBRL concepts for stock-based compensation."""
    return [
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
        "SharebasedCompensation",
        "StockBasedCompensation",
    ]


def find_values(facts: dict, concepts: list, namespace: str = "us-gaap") -> list:
    """Try multiple concepts and return the first one that has data."""
    for concept in concepts:
        vals = extract_annual_values(facts, concept, namespace)
        if vals:
            return vals
    return []


def values_by_fy(entries: list) -> dict:
    """Convert list of entries to dict keyed by fiscal year end date's year."""
    result = {}
    for e in entries:
        year = int(e["end"][:4])
        # Use the end-date year; for fiscal years ending Jan-Mar,
        # the calendar year might differ from fiscal year label
        fy = e.get("fy", year)
        result[fy] = e["val"]
    return result


def analyze_company(company: dict) -> dict:
    """
    Fetch Edgar data for a company and compare to analyst table values.
    """
    print(f"\n{'='*60}")
    print(f"Analyzing: {company['name']} ({company['ticker']})")
    print(f"{'='*60}")

    try:
        facts = fetch_company_facts(company["cik"])
    except Exception as e:
        print(f"  ERROR fetching Edgar data: {e}")
        return {"company": company["name"], "error": str(e)}

    # Extract revenue
    rev_entries = find_values(facts, get_revenue_concepts())
    rev_by_fy = values_by_fy(rev_entries)

    # Extract cost of revenue
    cost_entries = find_values(facts, get_cost_concepts())
    cost_by_fy = values_by_fy(cost_entries)

    # Extract operating income
    opinc_entries = find_values(facts, get_operating_income_concepts())
    opinc_by_fy = values_by_fy(opinc_entries)

    # Extract D&A
    da_entries = find_values(facts, get_da_concepts())
    da_by_fy = values_by_fy(da_entries)

    # Extract SBC
    sbc_entries = find_values(facts, get_sbc_concepts())
    sbc_by_fy = values_by_fy(sbc_entries)

    results = {
        "company": company["name"],
        "ticker": company["ticker"],
        "comparisons": [],
    }

    print(f"\n  Available fiscal years (revenue): {sorted(rev_by_fy.keys())}")

    # --- Compare Revenue ---
    # The table likely uses calendar year or fiscal year depending on company
    # Try FY2023 and FY2024
    for fy_label, fy_keys in [("FY2023", [2023, 2024]), ("FY2022", [2022, 2023])]:
        for fy in fy_keys:
            if fy in rev_by_fy:
                edgar_rev = rev_by_fy[fy] / 1e6  # Convert to millions
                print(f"\n  Edgar Revenue {fy_label} (end year {fy}): ${edgar_rev:,.1f}M")

                # Back-calculate analyst's implied 2023 revenue from EV/Rev 2023A
                if company["ev_rev_2023a"]:
                    implied_rev_2023 = company["ev"] / company["ev_rev_2023a"]
                    print(f"  Analyst implied 2023A Revenue (EV/EV_Rev): ${implied_rev_2023:,.1f}M")
                    pct_diff = (implied_rev_2023 - edgar_rev) / edgar_rev * 100
                    print(f"  Difference: {pct_diff:+.1f}%")
                    results["comparisons"].append({
                        "metric": f"Revenue {fy_label}",
                        "edgar_value": edgar_rev,
                        "analyst_implied": implied_rev_2023,
                        "pct_diff": pct_diff,
                    })
                break

    # --- Compare Gross Margin ---
    for fy in sorted(rev_by_fy.keys(), reverse=True):
        if fy in rev_by_fy and fy in cost_by_fy:
            rev = rev_by_fy[fy]
            cost = cost_by_fy[fy]
            edgar_gm = (rev - cost) / rev * 100
            print(f"\n  Edgar Gross Margin FY{fy}: {edgar_gm:.1f}%")
            print(f"  Analyst Gross Margin 2024E: {company['gross_margin_2024e']}%")

            if fy in (2024, 2025):  # Most likely match for "2024E"
                diff = company["gross_margin_2024e"] - edgar_gm
                print(f"  Difference: {diff:+.1f}pp")
                results["comparisons"].append({
                    "metric": f"Gross Margin FY{fy}",
                    "edgar_value": edgar_gm,
                    "analyst_value": company["gross_margin_2024e"],
                    "diff_pp": diff,
                })
            break

    # --- Compare EBITDA (GAAP vs Analyst) ---
    # GAAP EBITDA = Operating Income + D&A
    # Analyst adjusted EBITDA = GAAP EBITDA + SBC (+ other adjustments)
    for fy in sorted(rev_by_fy.keys(), reverse=True):
        if fy in opinc_by_fy:
            op_inc = opinc_by_fy[fy]
            da = da_by_fy.get(fy, 0)
            sbc = sbc_by_fy.get(fy, 0)
            rev = rev_by_fy.get(fy, 1)

            gaap_ebitda = op_inc + da
            adjusted_ebitda = gaap_ebitda + sbc

            gaap_ebitda_margin = gaap_ebitda / rev * 100
            adjusted_ebitda_margin = adjusted_ebitda / rev * 100

            print(f"\n  Edgar GAAP EBITDA FY{fy}: ${gaap_ebitda/1e6:,.1f}M (margin: {gaap_ebitda_margin:.1f}%)")
            print(f"  Edgar Adjusted EBITDA FY{fy} (+ SBC ${sbc/1e6:,.1f}M): ${adjusted_ebitda/1e6:,.1f}M (margin: {adjusted_ebitda_margin:.1f}%)")
            print(f"  Analyst EBITDA Margin 2024E: {company['ebitda_margin_2024e']}%")

            if company["ebitda_margin_2024e"] is not None:
                gaap_diff = company["ebitda_margin_2024e"] - gaap_ebitda_margin
                adj_diff = company["ebitda_margin_2024e"] - adjusted_ebitda_margin
                print(f"  Diff vs GAAP EBITDA margin: {gaap_diff:+.1f}pp")
                print(f"  Diff vs Adjusted EBITDA margin (+ SBC): {adj_diff:+.1f}pp")

                closer_to = "ADJUSTED (SBC added back)" if abs(adj_diff) < abs(gaap_diff) else "GAAP"
                print(f"  >> Analyst number is closer to: {closer_to}")

                results["comparisons"].append({
                    "metric": f"EBITDA Margin FY{fy}",
                    "edgar_gaap_ebitda_margin": gaap_ebitda_margin,
                    "edgar_adj_ebitda_margin": adjusted_ebitda_margin,
                    "analyst_value": company["ebitda_margin_2024e"],
                    "closer_to": closer_to,
                    "sbc_millions": sbc / 1e6,
                })
            break

    # --- Compare Revenue Growth ---
    years = sorted(rev_by_fy.keys())
    if len(years) >= 2:
        print(f"\n  Revenue history (Edgar):")
        for y in years[-4:]:
            print(f"    FY{y}: ${rev_by_fy[y]/1e6:,.1f}M")

        # Calculate growth rates
        for i in range(1, len(years)):
            prev_y, curr_y = years[i-1], years[i]
            growth = (rev_by_fy[curr_y] - rev_by_fy[prev_y]) / rev_by_fy[prev_y] * 100
            print(f"    Growth FY{prev_y}->FY{curr_y}: {growth:.1f}%")

            # Compare to analyst's 22A-23A growth
            if (prev_y == 2022 and curr_y == 2023) or (prev_y == 2023 and curr_y == 2024):
                analyst_growth = company["rev_growth_22a_23a"] if prev_y == 2022 else company["rev_growth_23a_24e"]
                diff = analyst_growth - growth
                print(f"    Analyst growth: {analyst_growth}%, Diff: {diff:+.1f}pp")
                results["comparisons"].append({
                    "metric": f"Revenue Growth FY{prev_y}-FY{curr_y}",
                    "edgar_value": growth,
                    "analyst_value": analyst_growth,
                    "diff_pp": diff,
                })

    return results


def print_summary(all_results: list):
    """Print a summary table of all comparisons."""
    print("\n" + "="*80)
    print("SUMMARY: ANALYST vs EDGAR COMPARISON")
    print("="*80)

    print("\n{:<20} {:<25} {:>12} {:>12} {:>10} {:<20}".format(
        "Company", "Metric", "Edgar", "Analyst", "Diff", "Notes"))
    print("-" * 100)

    ebitda_closer_to_adjusted = 0
    ebitda_closer_to_gaap = 0
    total_ebitda = 0

    for r in all_results:
        if "error" in r:
            print(f"{r['company']:<20} ERROR: {r['error']}")
            continue

        for comp in r.get("comparisons", []):
            metric = comp["metric"]
            company = r["company"][:18]

            if "EBITDA Margin" in metric:
                total_ebitda += 1
                closer = comp["closer_to"]
                if "ADJUSTED" in closer:
                    ebitda_closer_to_adjusted += 1
                else:
                    ebitda_closer_to_gaap += 1

                print(f"{company:<20} {metric:<25} "
                      f"{'GAAP:'+str(round(comp['edgar_gaap_ebitda_margin'],1)):>12} "
                      f"{comp['analyst_value']:>12} "
                      f"{'':>10} "
                      f"{closer}")
                print(f"{'':20} {'':25} "
                      f"{'ADJ:'+str(round(comp['edgar_adj_ebitda_margin'],1)):>12} "
                      f"{'':>12} "
                      f"{'':>10} "
                      f"SBC=${comp['sbc_millions']:.0f}M")
            elif "pct_diff" in comp:
                print(f"{company:<20} {metric:<25} "
                      f"{comp['edgar_value']:>12,.1f} "
                      f"{comp['analyst_implied']:>12,.1f} "
                      f"{comp['pct_diff']:>+9.1f}%")
            elif "diff_pp" in comp:
                edgar_val = comp["edgar_value"]
                analyst_val = comp["analyst_value"]
                print(f"{company:<20} {metric:<25} "
                      f"{edgar_val:>12.1f} "
                      f"{analyst_val:>12.1f} "
                      f"{comp['diff_pp']:>+9.1f}pp")

    if total_ebitda > 0:
        print(f"\n{'='*80}")
        print(f"EBITDA NORMALIZATION VERDICT:")
        print(f"  {ebitda_closer_to_adjusted}/{total_ebitda} companies' EBITDA margins are closer to ADJUSTED (SBC added back)")
        print(f"  {ebitda_closer_to_gaap}/{total_ebitda} companies' EBITDA margins are closer to GAAP")
        if ebitda_closer_to_adjusted > ebitda_closer_to_gaap:
            print(f"\n  >> CONCLUSION: The analyst table likely uses ADJUSTED EBITDA")
            print(f"     (adds back stock-based compensation to GAAP operating income + D&A)")
        else:
            print(f"\n  >> CONCLUSION: The analyst table appears to use GAAP-based EBITDA")


def main():
    all_results = []
    for i, company in enumerate(COMPANIES):
        result = analyze_company(company)
        all_results.append(result)
        # Rate limit: SEC Edgar asks for max 10 requests/sec
        if i < len(COMPANIES) - 1:
            time.sleep(0.5)

    print_summary(all_results)

    # Save raw results
    with open("analyst_vs_edgar_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nRaw results saved to analyst_vs_edgar_results.json")


if __name__ == "__main__":
    main()
