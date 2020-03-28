# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 18:18:54 2020

@author: pufks
"""

import pandas as pd
from marcap import marcap_data

def get_ydata(start, end):
    #start: 시작연도, end: 끝연도
    #반환은 재무제표를 합친 dataframe
    df_list = []
    for i in range(start, end + 1):
        fsfile = './data/Man_%sY.csv' % str(i)
        df = pd.read_csv(fsfile, dtype={'코드':str}, encoding='euc-kr')
        df_list.append(df)
        df_fs = pd.concat(df_list)
        df_fs.set_index('Date', inplace=True)
    return(df_fs)


Ticker = pd.read_csv('./data/MAN_Ticker.csv', dtype={'코드':str}, encoding='euc-kr')
Ticker = Ticker.iloc[:, 1:]
dtypes={'Close':float, 'Changes':float, 'ChagesRatio':float, 'Open':float, 'High':float, 'Low':float,
           'Volume':float, 'Amount':float, 'Marcap':float}
KOSPI = pd.read_csv('./data/kospi.csv', dtype=dtypes, parse_dates=['Date'], thousands=',')

start = 2003
end = 2017      #2003부터 2017까지 데이터 가능함
mf_count = 20 #마법공식으로 몇 종목을 선택할 지 결정하는 변수
seed_money = 20000000 #시뮬레이션을 위한 초기 자금
df_fs = get_ydata(start, end)
final_report = pd.Series(dtype=float)

for i in range(start, end+1):
    #마법공식을 적용하는 날(보고서 마감) 전일의 시총 계산
    endday = 31 #3월말 기준
    str_date_marcap = str(i+1) + '-03-' + str(endday)
    df_marcap = marcap_data(str_date_marcap)
    while len(df_marcap) == 0:
        endday = endday - 1
        str_date_marcap = str(i+1) + '-03-' + str(endday)
        df_marcap = marcap_data(str_date_marcap)
    price_marcap = df_marcap.loc[:,['Code', 'Marcap']]
    price_marcap['Marcap'] = price_marcap['Marcap'] / 100000000

    df_target = df_fs.loc[str(i)][['코드', '지배주주순이익', '법인세비용', '이자비용', '부채총계', '현금및현금성자산', '유동자산', '유동부채', '비유동자산', '감가상각비']]
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
    final_marcap = marcap_data(str(i+1)+'-04-01', str(i+2)+'-03-31')
    KOSPI = KOSPI[(str(i+1)+'-04-01' <= KOSPI['Date']) & (KOSPI['Date'] <= str(i+2)+'-03-31')]
    final_marcap = final_marcap[final_marcap['Code'].isin(mf_list)] #선정됙 종목의 marcap 정보만 추출
    df_yield = pd.DataFrame(columns=mf_list)    # 종목 코드를 column 이름으로 하는 dataframe 생성. 일자별 수익률 변화 체크
    df_yield['Date'] = KOSPI['Date']
    df_yield = df_yield.set_index('Date')
    df_asset = pd.Series(index=mf_list, dtype=float)    # 종목별 보유수량 체크
    balance = 0 #자산잔고

    for stock in mf_list:
            tmp_df = final_marcap[final_marcap['Code'] == stock]    #주가 정보를 포함하는 dataframe
            index_open = tmp_df.columns.get_loc('Open')
            index_stocks = tmp_df.columns.get_loc('Stocks')
            index_close = tmp_df.columns.get_loc('Close')
            index_changes = tmp_df.columns.get_loc('Changes')
            old_stocks = tmp_df.loc[tmp_df.index[0], 'Stocks']
            latest_stocks = tmp_df.loc[tmp_df.index[-1], 'Stocks']
            if old_stocks == latest_stocks:     #연간 주식수의 변화가 없으면 수정주가는 기존 주가를 사용
                tmp_df['Adj Close'] = tmp_df['Close']
                start_price = tmp_df.iat[0, index_open]
            else:           #연간 주식수 변화가 있으면 유상증자와 무상증자에 따라 수정주가 사용이 바뀜
                for k in range(len(tmp_df) - 1):
                    if tmp_df.iat[k, index_stocks] != tmp_df.iat[k + 1, index_stocks]:    #주식수의 변동이 있으면
                        if tmp_df.iat[k + 1, index_close] != (tmp_df.iat[k, index_close] + tmp_df.iat[k + 1, index_changes]):   #무상증자는 수정주가 계산이 필요함
                            latest_price = tmp_df.iat[k + 1, index_stocks]
                            tmp_df['Adj Close'] = tmp_df['Close'] * (tmp_df['Stocks'] / latest_price)  #수정종가
                            start_price = tmp_df.iat[0, index_open] * tmp_df.iat[0, index_stocks] / latest_price
                        else:   #유상증자는 수정주가 계산 필요 없음
                            tmp_df['Adj Close'] = tmp_df['Close']
                            start_price = tmp_df.iat[0, index_open]
             
            df_asset[stock] = moneyperstock * 0.99985 // start_price
            cash = cash + (moneyperstock - df_asset[stock] * start_price * 1.00015)
            tmp_df['Yield'] = tmp_df['Adj Close'] * df_asset[stock]
            df_yield[stock] = tmp_df['Yield']
            index_adj = tmp_df.columns.get_loc('Adj Close')
            balance = balance + tmp_df.iat[-1, index_adj] * df_asset[stock] * 0.99685
            #종목별로 수정주가를 계산하고 첫날을 기준으로 누적수익률을 체크
    df_yield = df_yield.fillna(method='ffill')
    df_yield['sum'] = df_yield.sum(axis=1)
    df_yield['sum'] = df_yield['sum'] + cash
    final_report = final_report.append(df_yield['sum'])
    
    seed_money = balance + cash
    print(i, seed_money)

final_report.plot()