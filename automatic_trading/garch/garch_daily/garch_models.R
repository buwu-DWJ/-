source('library.R')
library(hdf5r)
#参数
#test_length=1419-359
#all_length=1419
#garch_len=359
#test_length=1419-239
#all_length=1419
#garch_len=239
test_length=1419-119
all_length=1419
garch_len=119


#各类GARCH
# GARCH fGarch
garch_pred_armagarch=function(syn_of_this_etf,i)
{
  withTimeout(expr = {
    newdata=syn_of_this_etf$adj_lrtn[(i-garch_len):(i)]
    model <- garchFit(formula = ~ arma(1,1) + garch(1,1),
                      data=newdata,
                      include.mean = FALSE,
                      cond.dist = "sstd",
                      trace = FALSE)
    
    vol_now=tail(model@sigma.t,n=1)
    vol_pred=as.numeric(predict(model,n.ahead=1)[3])
    diff_vol_pred=(vol_pred-vol_now)/vol_now
    writeLines(paste0(i))
    c(diff_vol_pred)
  },
  timeout = 10)
}
# apARCH fGarch
garch_pred_armaaparch=function(syn_of_this_etf,i)
{
  withTimeout(expr = {
    newdata=syn_of_this_etf$adj_lrtn[(i-garch_len):(i)]
    model <- garchFit(formula = ~ arma(1,1) + aparch(1,1),
                      data=newdata,
                      include.mean = FALSE,
                      cond.dist = "sstd",
                      trace = FALSE)
    
    vol_now=tail(model@sigma.t,n=1)
    vol_pred=as.numeric(predict(model,n.ahead=1)[3])
    diff_vol_pred=(vol_pred-vol_now)/vol_now
    print(i)
    c(diff_vol_pred)
  },
  timeout = 10)
}
# ARMA-GARCHs rugarch
# 总执行rugarch
garch_pred_rugarch=function(syn_of_this_etf,i,spec)
{
  withTimeout(expr = {
    newdata=syn_of_this_etf$adj_lrtn[(i-garch_len):(i)]
    # model <- ugarchfit(spec = spec,
    #                    data = newdata,
    #                    solver = "hybrid")
    model <- ugarchfit(spec = spec,
                       data = newdata,
                       solver = "hybrid")
    vol_now=tail(model@fit$sigma,n=1)
    vol_pred=as.numeric(ugarchforecast(model,n.ahead=1)@forecast$sigmaFor)
    diff_vol_pred=(vol_pred-vol_now)/vol_now
    print(i)
    print(spec)
    c(diff_vol_pred)
  },
  timeout = 10)
  
}
# ARMA-GJR-GARCH
spec_gjrgarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                              include.mean = FALSE),
                            variance.model = list(model = "gjrGARCH",
                                                  garchOrder = c(1,1)),
                            distribution.model = "sstd")
# ARMA-csGARCH
spec_csgarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                             include.mean = FALSE),
                           variance.model = list(model = "csGARCH",
                                                 garchOrder = c(1,1)),
                           distribution.model = "sstd")
# ARMA-fGARCH
options(warn = -1)
submodels=c("NAGARCH","TGARCH")
for(thissubmodel in submodels)
{
  #writeLines(paste0("bin_arma_fgarch_",thissubmodel))
  tmp_model=ugarchspec(mean.model = list(armaOrder=c(1,1),
                                         include.mean = FALSE),
                       variance.model = list(model = "fGARCH",
                                             garchOrder = c(1,1),
                                             submodel = thissubmodel),
                       distribution.model = "sstd")
  assign(paste0("spec_fgarch_",thissubmodel),tmp_model)
}


syn_future_510300 = read.csv('a.csv')
t1=proc.time()
#执行计算
#for(etf_name in c(510050,510300))
for(etf_name in c(510300))
{
  cl <- makeCluster(detectCores()-1)
  registerDoParallel(cl) #注册并开始并行计算
  writeLines(paste0("Calculating preds for ",etf_name, " syn_future."))
  syn_of_this_etf=get(paste0("syn_future_",etf_name))
  t1=proc.time()
  
  #开始算六个模型
  bin_arma_garch_f=foreach(i=c((all_length-test_length+1):all_length),
                           .combine='rbind',
                           .packages=c("fGarch","R.utils")) %dopar% c(i,try(garch_pred_armagarch(syn_of_this_etf,i)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("GARCH","\t",t[3][[1]],'s'))
  
  
  bin_arma_aparch_f=foreach(i=c((all_length-test_length+1):all_length),
                            .combine='rbind',
                            .packages=c("fGarch","R.utils")) %dopar% c(i,try(garch_pred_armaaparch(syn_of_this_etf,i)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("apARCH","\t",t[3][[1]],'s'))
  
  
  bin_arma_gjrgarch=foreach(i=c((all_length-test_length+1):all_length),
                            .combine='rbind',
                            .packages=c("rugarch","R.utils")) %dopar% c(i,try(garch_pred_rugarch(syn_of_this_etf,i,spec = spec_gjrgarch)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("GJR-GARCH","\t",t[3][[1]],'s'))
  
  
  bin_arma_csgarch=foreach(i=c((all_length-test_length+1):all_length),
                           .combine='rbind',
                           .packages=c("rugarch","R.utils")) %dopar% c(i,try(garch_pred_rugarch(syn_of_this_etf,i,spec = spec_csgarch)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("csGARCH","\t",t[3][[1]],'s'))
  
  
  bin_arma_nagarch=foreach(i=c((all_length-test_length+1):all_length),
                           .combine='rbind',
                           .packages=c("rugarch","R.utils")) %dopar% c(i,try(garch_pred_rugarch(syn_of_this_etf,i,spec = spec_fgarch_NAGARCH)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("naGARCH","\t",t[3][[1]],'s'))
  
  
  bin_arma_tgarch=foreach(i=c((all_length-test_length+1):all_length),
                          .combine='rbind',
                          .packages=c("rugarch","R.utils")) %dopar% c(i,try(garch_pred_rugarch(syn_of_this_etf,i,spec = spec_fgarch_TGARCH)))
  t2=proc.time()
  t=t2-t1
  writeLines(paste0("tGARCH","\t",t[3][[1]],'s'))
  
  selected_models=c("arma_GARCH_f","arma_apARCH_f","arma_csGARCH_r",
                    "arma_gjrGARCH_r","arma_f_naGARCH_r","arma_f_tGARCH_r" )
  preds=data.frame(#syn_of_this_etf$datetime[(all_length-test_length+1):all_length],
                   bin_arma_garch_f[,1],
                   #fgarch
                   bin_arma_garch_f[,2],
                   bin_arma_aparch_f[,2],
                   #rugarch
                   bin_arma_csgarch[,2],
                   bin_arma_gjrgarch[,2],
                   #rugarch_f
                   bin_arma_nagarch[,2],
                   bin_arma_tgarch[,2])
  colnames(preds)=c("datetime",selected_models)
  for(j in selected_models)
  {
    preds[,j]=as.numeric(preds[,j])
  }
  #if(any(is.na(preds)))
  #{
  #  preds[is.na(preds)]=0
  #}
  assign(x = paste0("preds_",etf_name),value = preds)
  stopCluster(cl)
}

write.csv(preds,"b_120.csv", row.names=F, quote=F)