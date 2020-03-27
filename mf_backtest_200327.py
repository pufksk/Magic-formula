# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 18:18:54 2020

@author: pufks
"""

import pandas as pd
from marcap import marcap_data

Ticker = pd.read_csv('./data/MAN_Ticker.csv', dtype={'코드':str}, encoding='euc-kr')
Ticker = Ticker.iloc[:, 1:]

df_fs = pd.read_csv('./data/Man_2003Y.csv', dtype={'코드':str}, encoding='euc-kr')
df_fs = df_fs.iloc[:, 1:]
df_fs.set_index('Date', inplace=True)

mf_count = 20 #마법공식으로 몇 종목을 선택할 지 결정하는 변수
seed_money = 20000000 #시뮬레이션을 위한 초기 자금
df_marcap = marcap_data('2004-03-31')
price_marcap = df_marcap.loc[:,['Code', 'Marcap']]
price_marcap['Marcap'] = price_marcap['Marcap'] / 100000000

df_target = df_fs.loc['2003'][['코드', '지배주주순이익', '법인세비용', '이자비용', '부채총계', '현금및현금성자산', '유동자산', '유동부채', '비유동자산', '감가상각비']]
df_target = pd.merge(df_target, price_marcap, left_on='코드', right_on='Code')
df_target = df_target.drop(columns=['Code'])
df_target['EXCASH1'] = df_target['유동부채'] - df_target['유동자산'] + df_target['현금및현금성자산']
df_target.loc[df_target['EXCASH1'] < 0, 'EXCASH1'] = 0
df_target['EBIT'] = df_target['지배주주순이익'] + df_target['법인세비용'] + df_target['이자비용']
df_target['IC'] = df_target['유동자산'] - df_target['유동부채'] + df_target['비유동자산'] - df_target['감가상각비']
df_target['EV'] = df_target['Marcap'] + df_target['부채총계'] - df_target['현금및현금성자산'] + df_target['EXCASH1']
df_target['EY'] = df_target['EBIT'] / df_target['EV']
df_target['ROC'] = df_target['EBIT'] / df_target['IC']
df_target['RANK_EY'] = df_target['EY'].rank(ascending=False)
df_target['RANK_ROC'] = df_target['ROC'].rank(ascending=False)
df_target['RANK_TOT'] = df_target['RANK_EY'] + df_target['RANK_ROC']
df_target = pd.merge(df_target, Ticker, left_on='코드', right_on='코드')
df_last = df_target.sort_values(by=['RANK_TOT']).head(mf_count)
df_last = df_last.set_index('코드')

moneyperstock = seed_money / mf_count #종목별 투자액
cash = 0 # 초기 현금잔고
mf_list = df_last.index.tolist() # 선택된 종목의 코드를 리스트
final_marcap = marcap_data('2004-04-01', '2005-03-31')
final_marcap = final_marcap[final_marcap['Code'].isin(mf_list)] #선정됙 종목의 marcap 정보만 추출
df_yield = pd.DataFrame(columns=mf_list)    # 종목 코드를 column 이름으로 하는 dataframe 생성. 일자별 수익률 변화 체크
df_asset = pd.Series(index=mf_list, dtype=float)    # 종목별 보유수량 체크
balance = 0 #자산잔고

for stock in mf_list:
        tmp_df = final_marcap[final_marcap['Code'] == stock]    #주가 정보를 포함하는 df
        old_stocks = tmp_df.loc[tmp_df.index[0], 'Stocks']
        latest_stocks = tmp_df.loc[tmp_df.index[-1], 'Stocks']
        if old_stocks == latest_stocks:     #연간 주식수의 변화가 없으면 수정주가는 기존 주가를 사용
            tmp_df['Adj Close'] = tmp_df['Close']
            start_price = tmp_df.loc[tmp_df.index[0], 'Open']
            df_asset[stock] = moneyperstock * 0.99985 // start_price
            cash = cash + (moneyperstock - df_asset[stock] * start_price * 1.00015)
            tmp_df['Yield'] = tmp_df['Close'] * df_asset[stock]
            df_yield[stock] = tmp_df['Yield']
            balance = balance + tmp_df.loc[tmp_df.index[-1], 'Close'] * df_asset[stock] * 0.99685
        else:           #연간 주식수 변화가 있으면 유상증자와 무상증자에 따라 수정주가 사용이 바뀜
            change_count = 0
            for k in range(len(tmp_df) - 1):
                if tmp_df.loc[tmp_df.index[k], 'Stocks'] != tmp_df.loc[tmp_df.index[k+1], 'Stocks']:    #주식수의 변동이 있으면
                    before_mar = tmp_df.loc[tmp_df.index[k], 'Marcap'] * (1 + tmp_df.loc[tmp_df.index[k+1], 'ChagesRatio'] / 100)
                    after_mar = tmp_df.loc[tmp_df.index[k+1], 'Marcap']
                    if change_count == 0:
                        if (after_mar * 0.99 < before_mar) & (before_mar < after_mar * 1.01):   #무상증자는 수정주가 계산이 필요함
                            start_price = tmp_df.loc[tmp_df.index[0], 'Open'] * tmp_df.loc[tmp_df.index[0], 'Stocks'] / tmp_df.loc[tmp_df.index[k+1], 'Stocks']
                            tmp_df['Adj Close'] = tmp_df['Close'] * (tmp_df.loc[tmp_df.index[k], 'Stocks'] / tmp_df.loc[tmp_df.index[k+1], 'Stocks'])  #수정종가
                        else:   #유상증자는 수정주가 계산 필요 없음
                            tmp_df['Adj Close'] = tmp_df['Close']
                            start_price = tmp_df.loc[tmp_df.index[0], 'Open']
                        change_count += 1
                    else:   # 주식수 변동이 여러번 있으면 수정주가가 기존 종가를 계속 사용할 수 없으므로 기존 종가 대신 기존 수정주가를 이용해 다시 계산
                        if (after_mar * 0.99 < before_mar) & (before_mar < after_mar * 1.01):
                            start_price = start_price * tmp_df.loc[tmp_df.index[k], 'Stocks'] / tmp_df.loc[tmp_df.index[k+1], 'Stocks']
                            tmp_df['Adj Close'] = tmp_df['Adj Close'] * (tmp_df.loc[tmp_df.index[k], 'Stocks'] / tmp_df.loc[tmp_df.index[k+1], 'Stocks'])  #수정종가
                        else:
                            start_price = start_price
                            tmp_df['Adj Close'] = tmp_df['Adj Close']
                        change_count += 1  
            df_asset[stock] = moneyperstock * 0.99985 // start_price
            cash = cash + (moneyperstock - df_asset[stock] * start_price * 1.00015)
            tmp_df['Yield'] = tmp_df['Adj Close'] * df_asset[stock]
            df_yield[stock] = tmp_df['Yield']
            balance = balance + tmp_df.loc[tmp_df.index[-1], 'Adj Close'] * df_asset[stock] * 0.99685
            #종목별로 수정주가를 계산하고 첫날을 기준으로 누적수익률을 체크
df_yield = df_yield.fillna(method='ffill')
df_yield['sum'] = df_yield.sum(axis=1)
df_yield['sum'] = df_yield['sum'] + cash

seed_money = balance + cash
print(seed_money)

df_yield['sum'].plot()