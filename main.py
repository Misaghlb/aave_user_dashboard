from datetime import datetime
from enum import Enum

import pandas as pd
import plotly.express as px
import pytz
import requests
import streamlit as st

st.set_page_config(page_title='Aave User Dashboard', layout='wide', page_icon=':dollar:')
st.title("Aave v2, v3 User Dashboard - All chains in one")


class Chain(Enum):
    Ethereum = 'Ethereum'
    Optimism = 'Optimism'
    Arbitrum = 'Arbitrum'
    Polygon_v3 = 'Polygon v3'
    Polygon_V2 = 'Polygon v2'
    Avalanche_v2 = 'Avalanche v2'
    Avalanche_v3 = 'Avalanche v3'
    Harmony = 'Harmony'
    Fantom = 'Fantom'


def get_chain_info(chain_name: Chain):
    if chain_name == Chain.Avalanche_v2:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v2-avalanche',
                'https://snowtrace.io/address/',
                'https://snowtrace.io/tx/'
                ]
    if chain_name == Chain.Avalanche_v3:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-avalanche',
                'https://snowtrace.io/address/',
                'https://snowtrace.io/tx/'
                ]
    if chain_name == Chain.Ethereum:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v2',
                'https://etherscan.io/address/',
                'https://etherscan.io/tx/'
                ]
    if chain_name == Chain.Optimism:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-optimism',
                'https://optimistic.etherscan.io/address/',
                'https://optimistic.etherscan.io/tx/'
                ]
    if chain_name == Chain.Polygon_v3:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-polygon',
                'https://polygonscan.com/address/',
                'https://polygonscan.com/tx/'
                ]
    if chain_name == Chain.Polygon_V2:
        return ['https://api.thegraph.com/subgraphs/name/aave/aave-v2-matic',
                'https://polygonscan.com/address/',
                'https://polygonscan.com/tx/'
                ]
    if chain_name == Chain.Harmony:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-harmony',
                'https://explorer.harmony.one/address/',
                'https://explorer.harmony.one/tx/'
                ]
    if chain_name == Chain.Fantom:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-fantom',
                'https://ftmscan.com/address/',
                'https://ftmscan.com/tx/'
                ]
    if chain_name == Chain.Arbitrum:
        return ['https://api.thegraph.com/subgraphs/name/aave/protocol-v3-arbitrum',
                'https://arbiscan.io/address/',
                'https://arbiscan.io/tx/'
                ]


def fetch_asset_price(asset_id: str):
    payload = {"query": """
               {
             tokens(first: 5
               where:{symbol: \"%s\"}
           
             ) {
               id
               name
               symbol
               decimals
               priceUSD
               priceTimestamp
             }
           }
           """ % (asset_id)
               }
    res = requests.post(url='https://api.thegraph.com/subgraphs/name/wardenluna/token-prices-optimism',
                        json=payload).json()
    return float(res['data']['tokens'][0]['priceUSD'])


def clean_reserves(reserves, usdPriceEth):
    result = []
    for raw_item in reserves:
        item = {}
        item['symbol'] = raw_item['reserve']['symbol']
        item['decimals'] = float(raw_item['reserve']['decimals'])
        item['amount'] = float(raw_item['currentATokenBalance']) / pow(10, item['decimals'])
        item['debt'] = float(raw_item['currentTotalDebt']) / pow(10, float(raw_item['reserve']['decimals']))
        # if selected_chain in (Chain.Polygon_v3, Chain.Arbitrum, Chain.Fantom, Chain.Harmony, Chain.Avalanche_v3):
        if selected_chain not in (Chain.Ethereum, Chain.Polygon_V2, Chain.Optimism):
            usd_price = float(raw_item['reserve']['price']['priceInEth']) / pow(10, 8)
        elif selected_chain == Chain.Optimism:
            usd_price = fetch_asset_price(item['symbol'])
        else:
            usd_price = float(raw_item['reserve']['price']['priceInEth']) / pow(10, 18) / usdPriceEth

        item['amount_usd'] = float(item['amount']) * usd_price
        item['debt_usd'] = float(item['debt']) * usd_price
        result.append(item)
    return result


def clean_deposits(deposits, usdPriceEth):
    result = []
    for raw_item in deposits:
        item = {}
        item['py_date'] = datetime.fromtimestamp(int(raw_item['timestamp']), pytz.timezone("UTC"))
        item['str_date'] = datetime.fromtimestamp(int(raw_item['timestamp']), pytz.timezone("UTC")).strftime('%Y/%m/%d')
        item['symbol'] = raw_item['reserve']['symbol']
        item['decimals'] = float(raw_item['reserve']['decimals'])
        item['amount'] = float(raw_item['amount']) / pow(10, item['decimals'])
        if selected_chain not in (Chain.Ethereum, Chain.Polygon_V2):
            usd_price = float(raw_item['reserve']['price']['priceInEth']) / pow(10, 8)
        elif selected_chain == Chain.Optimism:
            usd_price = fetch_asset_price(item['symbol'])
        else:
            usd_price = float(raw_item['reserve']['price']['priceInEth']) / pow(10, 18) / usdPriceEth
        # priceInEth = float(raw_item['reserve']['price']['priceInEth']) / pow(10, 18)
        item['amount_usd'] = float(item['amount']) * usd_price
        result.append(item)
    return result


def fetch_eth_price():
    payload = {
        "query": """{
      priceOracles{
        usdPriceEth
      }
    }
    """
    }
    res = requests.post(url=get_chain_info(Chain.Ethereum)[0],
                        json=payload).json()
    return int(res['data']['priceOracles'][0]['usdPriceEth']) / pow(10, 18)


if 'usdPriceEth' not in st.session_state:
    st.session_state.usdPriceEth = fetch_eth_price()


@st.cache(ttl=6 * 60 * 60, suppress_st_warning=True)  # 6 hours
def fetch_data(chain: Chain, user_address: str):
    deposit_str = 'depositHistory' if chain in (
        Chain.Ethereum, Chain.Avalanche_v2, Chain.Polygon_V2) else 'supplyHistory'
    payload = {
        "query": """{
  users
      (where: { id: \"%s\", })
  {
    
    reserves {
        reserve {
         symbol decimals price  {
          priceInEth oracle{
            usdPriceEth 
          }
          priceInEth
         }
        }   
      currentATokenBalance
      currentTotalDebt
    }
    
    %s
    ( orderBy: timestamp
      orderDirection: desc)
    {
      timestamp amount reserve {
        symbol decimals price{priceInEth} 
      }
    }
    
     borrowHistory
    ( orderBy: timestamp
      orderDirection: desc)
    {
      timestamp amount reserve {
        symbol decimals price{priceInEth} 
      }
    }
    repayHistory
    ( orderBy: timestamp
      orderDirection: desc)
    {
      timestamp amount reserve {
        symbol decimals price{priceInEth} 
      }
    }
    redeemUnderlyingHistory
    ( orderBy: timestamp
      orderDirection: desc)
    {
      timestamp amount reserve {
        symbol decimals price{priceInEth} 
      }
    }
  }
  
}
""" % (user_address.lower(), deposit_str)
    }
    res = requests.post(url=get_chain_info(chain)[0],
                        json=payload).json()
    # st.write(res)
    res = res["data"]
    try:
        reserves = res["users"][0]['reserves']
        depositHistory = res["users"][0][deposit_str]
        borrowHistory = res["users"][0]['borrowHistory']
        repayHistory = res["users"][0]['repayHistory']
        redeemUnderlyingHistory = res["users"][0]['redeemUnderlyingHistory']

        reserves = clean_reserves(reserves, st.session_state.usdPriceEth)
        deposits = clean_deposits(depositHistory, st.session_state.usdPriceEth)
        borrows = clean_deposits(borrowHistory, st.session_state.usdPriceEth)
        repays = clean_deposits(repayHistory, st.session_state.usdPriceEth)
        withdraws = clean_deposits(redeemUnderlyingHistory, st.session_state.usdPriceEth)
    except Exception as e:
        # st.write(e)
        st.warning("user not found")
        return False

    return [reserves, deposits, borrows, repays, withdraws]


def get_type_name(item: str):
    return item[:-1].capitalize()


def get_explorer_user_address(user_address: str, chain):
    return str(get_chain_info(chain)[1] + user_address)


def get_explorer_transaction_address(transaction_address: str, chain):
    return get_chain_info(chain)[2] + transaction_address


def clean_data(res, chain):
    actions = []
    for item in ['withdraws', 'deposits', 'borrows', 'repays', 'liquidates']:
        if not res[item]:
            continue
        action_content_list = res[item]
        for action in action_content_list:
            clean_action = {}
            clean_action['Time'] = datetime.fromtimestamp(int(action['timestamp']), ).strftime(
                "%m/%d/%Y, %H:%M:%S")
            clean_action['py_date'] = datetime.fromtimestamp(int(action['timestamp']), pytz.timezone("UTC"))
            clean_action['Type'] = get_type_name(item)
            clean_action['Asset Symbol'] = action['asset']['symbol']
            clean_action['transaction_hash'] = action['hash']
            clean_action['Asset ID'] = action['asset']['id']
            clean_action['Asset Amount'] = float(int(action['amount']) / pow(10, int(action['asset']['decimals'])))
            clean_action['Amount USD'] = action['amountUSD']
            clean_action['user'] = action['account']['id']
            clean_action['logIndex'] = action['logIndex']
            clean_action['chain'] = chain.value
            actions.append(clean_action)
    return actions


ex = st.expander('About')
ex.title('How it works')
ex.markdown(
    "If a user address is entered, the app will search for the user data on thegraph.com (Aave subgraph) chain data across all chains supported by Aave.  \n"
    "by this approach we have the most recent data  as soon as they occure, the feature that is not exist on Dune and Flipside(about one day delay)  \n"
    "**Chains**: Ethereum, Polygon(v2,v3), Avalanche(v2,v3), Optimism, Arbitrum, Harmony, Fantom  \n"
    "**Transaction Types**: Deposit, Withdraw, Borrow, Repay")

st.markdown('---')


def generate_supply_charts(data):
    if not data:
        return
    c1, c2, c3 = st.columns(3)

    df_deposits = pd.DataFrame(
        data[1],
        columns=["py_date", "str_date", "symbol", "amount", "amount_usd"]).sort_values('py_date')

    df_borrows = pd.DataFrame(
        data[2],
        columns=["py_date", "str_date", "symbol", "amount", "amount_usd"]).sort_values('py_date')

    df_repays = pd.DataFrame(
        data[3],
        columns=["py_date", "str_date", "symbol", "amount", "amount_usd"]).sort_values('py_date')

    df_withdraws = pd.DataFrame(
        data[4],
        columns=["py_date", "str_date", "symbol", "amount", "amount_usd"]).sort_values('py_date')

    df_lended = pd.DataFrame(
        data[0],
        columns=["symbol", "amount", "amount_usd", "debt_usd", "debt"]).sort_values('amount_usd', ascending=False)
    st.markdown('---')

    c1.header("Available Lending Assets")
    c1.table(df_lended)

    fig = px.pie(df_lended, values='amount_usd', names='symbol', title="Current Lended Assets in USD",
                 template='seaborn')
    fig.update_traces(textposition='inside', textinfo='value+label', insidetextorientation='radial')
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c2.plotly_chart(fig, use_container_width=True)

    fig = px.pie(df_lended, values='debt_usd', names='symbol', title="Current Debt in USD",
                 template='seaborn')
    fig.update_traces(textposition='inside', textinfo='value+label', insidetextorientation='radial')
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c3.plotly_chart(fig, use_container_width=True)
    # ---------------------------- Deposits
    c1, c2 = st.columns(2)
    fig = px.bar(df_deposits, x='str_date', y='amount', color='symbol', title="Daily Deposit",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    c1.plotly_chart(fig, use_container_width=True)

    fig = px.bar(df_deposits, x='str_date', y='amount_usd', color='symbol', title="Daily Deposit in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    c2.plotly_chart(fig, use_container_width=True)

    # ----------------------------- Withdrawals
    fig = px.bar(df_withdraws, x='str_date', y='amount', color='symbol', title="Daily Withdrawals",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c1.plotly_chart(fig, use_container_width=True)

    fig = px.bar(df_withdraws, x='str_date', y='amount_usd', color='symbol', title="Daily Withdrawals in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c2.plotly_chart(fig, use_container_width=True)

    # ----------------------- Borrow
    fig = px.bar(df_borrows, x='str_date', y='amount', color='symbol', title="Daily Borrow",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c1.plotly_chart(fig, use_container_width=True)

    fig = px.bar(df_borrows, x='str_date', y='amount_usd', color='symbol', title="Daily Borrow in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c2.plotly_chart(fig, use_container_width=True)
    #  ----------------------------------- Repay
    fig = px.bar(df_repays, x='str_date', y='amount', color='symbol', title="Daily Repay",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c1.plotly_chart(fig, use_container_width=True)

    fig = px.bar(df_repays, x='str_date', y='amount_usd', color='symbol', title="Daily Repay in USD",
                 template='seaborn')
    fig.update_traces(hovertemplate=None)
    fig.update_layout(hovermode="x unified")
    fig.update_layout(title_x=0, margin=dict(l=0, r=10, b=30, t=30), yaxis_title=None, xaxis_title=None)
    c2.plotly_chart(fig, use_container_width=True)
    #  -------------------------------


with st.spinner('Updating Dashboard...'):
    c1, c2, c3 = st.columns((1, 2, 1))

    with c2.form("my_form"):
        activation_function = st.selectbox('Choose a Chain',
                                           ['Ethereum', 'Polygon v2', 'Polygon v3', 'Arbitrum', 'Optimism',
                                            'Avalanche v2',
                                            'Avalanche v3', 'Fantom', 'Harmony'])

        input_user_address = st.text_input('Enter User Address:',
                                           '0x429801692ae55c2d706cf57276fe9f71abcce3cc',
                                           placeholder='Input the User Address')
        submitted = st.form_submit_button("Submit")


    st.markdown('---')

    if activation_function == 'Ethereum':
        selected_chain = Chain.Ethereum
        chart_data = fetch_data(Chain.Ethereum, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Avalanche v2':
        selected_chain = Chain.Avalanche_v2
        chart_data = fetch_data(Chain.Avalanche_v2, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Avalanche v3':
        selected_chain = Chain.Avalanche_v3
        chart_data = fetch_data(Chain.Avalanche_v3, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Optimism':
        selected_chain = Chain.Optimism
        chart_data = fetch_data(Chain.Optimism, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Polygon v3':
        selected_chain = Chain.Polygon_v3
        chart_data = fetch_data(Chain.Polygon_v3, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Polygon v2':
        selected_chain = Chain.Polygon_V2
        chart_data = fetch_data(Chain.Polygon_V2, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Harmony':
        selected_chain = Chain.Harmony
        chart_data = fetch_data(Chain.Harmony, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Fantom':
        selected_chain = Chain.Fantom
        chart_data = fetch_data(Chain.Fantom, input_user_address)
        generate_supply_charts(chart_data)

    if activation_function == 'Arbitrum':
        selected_chain = Chain.Arbitrum
        chart_data = fetch_data(Chain.Arbitrum, input_user_address)
        generate_supply_charts(chart_data)

# # end
st.write('')
st.write('')
st.write('')
st.write('')
st.write('')
st.write('')
st.write('')
st.write('')
st.markdown("---")
st.markdown("##### Contact:\n"
            "- developed by Misagh lotfi \n"
            "- https://twitter.com/misaghlb \n"
            "- misaghlb@live.com\n"
            "- https://www.linkedin.com/in/misagh-lotfi/\n"
            )

st.markdown("##### Sources:\n"
            "- https://thegraph.com/hosted-service/subgraph/aave/protocol-v2 \n"
            "- https://api.thegraph.com/subgraphs/name/wardenluna/token-prices-optimism \n"
            "- code: https://github.com/Misaghlb/aave_user_dashboard \n"
            )
