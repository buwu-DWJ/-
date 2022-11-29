source('library.R')
library(hdf5r)
#参数
#test_length=1419-359
#all_length=1419
#garch_len=359
test_length=1419-239
all_length=1419
garch_len=239
#test_length=1419-119
#all_length=1419
#garch_len=119

syn_future = read.csv('a.csv')
options(warn = -1)
options(digits=7)

garch_pred_garch=function(i)
{
  newdata=syn_future$adj_lrtn[(i-garch_len):(i)]
  model <- garchFit(formula = ~ garch(1,1),
                    data=newdata,
                    include.mean = FALSE,
                    cond.dist = "sstd",
                    trace = FALSE)  
  
  vol_now=tail(model@sigma.t,n=1)
  vol_pred=as.numeric(predict(model,n.ahead=1)[3])
  diff_vol_pred=(vol_pred-vol_now)/vol_now
  c(diff_vol_pred)
}

garch_pred_aparch=function(i)
{
  newdata=syn_future$adj_lrtn[(i-garch_len):(i)]
  model <- garchFit(formula = ~ aparch(1,1),
                    data=newdata,
                    include.mean = FALSE,
                    cond.dist = "sstd",
                    trace = FALSE)  
  vol_now=tail(model@sigma.t,n=1)
  vol_pred=as.numeric(predict(model,n.ahead=1)[3])
  diff_vol_pred=(vol_pred-vol_now)/vol_now
  c(diff_vol_pred)
}

garch_pred_armagarch=function(i)
{
  newdata=syn_future$adj_lrtn[(i-garch_len):(i)]
  model <- garchFit(formula = ~ arma(1,1) + garch(1,1),
                    data=newdata,
                    include.mean = FALSE,
                    cond.dist = "sstd",
                    trace = FALSE)  
  vol_now=tail(model@sigma.t,n=1)
  vol_pred=as.numeric(predict(model,n.ahead=1)[3])
  diff_vol_pred=(vol_pred-vol_now)/vol_now
  c(diff_vol_pred)
}

garch_pred_armaaparch=function(i)
{
  newdata=syn_future$adj_lrtn[(i-garch_len):(i)]
  model <- garchFit(formula = ~ arma(1,1) + aparch(1,1),
                    data=newdata,
                    include.mean = FALSE,
                    cond.dist = "sstd",
                    trace = FALSE)  
  vol_now=tail(model@sigma.t,n=1)
  vol_pred=as.numeric(predict(model,n.ahead=1)[3])
  diff_vol_pred=(vol_pred-vol_now)/vol_now
  c(diff_vol_pred)
}

t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_garch_f=foreach(i=c((garch_len+1):length(syn_future[,1])),
                    .combine='rbind',
                    .packages=c("fGarch")) %dopar% c(i,try(garch_pred_garch(i)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))

t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_aparch_f=foreach(i=c((garch_len+1):length(syn_future[,1])),
                     .combine='rbind',
                     .packages=c("fGarch")) %dopar% c(i,try(garch_pred_aparch(i)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))

t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_garch_f=foreach(i=c((garch_len+1):length(syn_future[,1])),
                         .combine='rbind',
                         .packages=c("fGarch")) %dopar% c(i,try(garch_pred_armagarch(i)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))

t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_aparch_f=foreach(i=c((garch_len+1):length(syn_future[,1])),
                          .combine='rbind',
                          .packages=c("fGarch")) %dopar% c(i,try(garch_pred_armaaparch(i)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
options(warn = 1)

# ARMA-GARCHs rugarch

garch_pred_rugarch=function(i,spec)
{
  newdata=syn_future$adj_lrtn[(i-garch_len):(i)]
  model <- ugarchfit(spec = spec, 
                     data = newdata,
                     solver = "hybrid")
  vol_now=tail(model@fit$sigma,n=1)
  vol_pred=as.numeric(ugarchforecast(model,n.ahead=1)@forecast$sigmaFor)
  diff_vol_pred=(vol_pred-vol_now)/vol_now
  c(diff_vol_pred)
}

# ARMA-sGARCH
options(warn = -1)
spec_sgarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                            include.mean=FALSE),
                          variance.model = list(model = "sGARCH",
                                                garchOrder = c(1,1)),
                          distribution.model = "sstd")
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_sgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_sgarch)))
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()


# ARMA-eGARCH
spec_egarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                            include.mean = FALSE),
                          variance.model = list(model = "eGARCH",
                                                garchOrder = c(1,1)),
                          distribution.model = "sstd")
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_egarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_egarch)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-GJR-GARCH

spec_gjrgarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                              include.mean = FALSE),
                            variance.model = list(model = "gjrGARCH",
                                                  garchOrder = c(1,1)),
                            distribution.model = "sstd")
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_gjrgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                          .combine='rbind',
                          .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_gjrgarch)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-apARCH
spec_aparch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                            include.mean = FALSE),
                          variance.model = list(model = "apARCH",
                                                garchOrder = c(1,1)),
                          distribution.model = "sstd")

cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
t1=proc.time()
bin_arma_aparch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_aparch)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-IGARCH
spec_igarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                            include.mean = FALSE),
                          variance.model = list(model = "iGARCH",
                                                garchOrder = c(1,1)),
                          distribution.model = "sstd")
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_igarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_igarch)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-csGARCH
spec_csgarch <- ugarchspec(mean.model = list(armaOrder=c(1,1),
                                             include.mean = FALSE),
                           variance.model = list(model = "csGARCH",
                                                 garchOrder = c(1,1)),
                           distribution.model = "sstd")
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_csgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                         .combine='rbind',
                         .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_csgarch)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-fGARCH
options(warn = -1)
submodels=c("AVGARCH","NGARCH","NAGARCH","ALLGARCH","TGARCH")
for(thissubmodel in submodels)
{
  writeLines(paste0("bin_arma_fgarch_",thissubmodel))
  tmp_model=ugarchspec(mean.model = list(armaOrder=c(1,1),
                                         include.mean = FALSE),
                       variance.model = list(model = "fGARCH",
                                             garchOrder = c(1,1),
                                             submodel = thissubmodel),
                       distribution.model = "sstd")
  assign(paste0("spec_fgarch_",thissubmodel),tmp_model)
}

# ARMA-fGARCH-AVGARCH
options(warn = -1)
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算length(syn_future[,1])
bin_arma_avgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                         .combine='rbind',
                         .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_fgarch_AVGARCH)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-fGARCH-NGARCH
options(warn = -1)

t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_ngarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_fgarch_NGARCH)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()


# ARMA-fGARCH-NAGARCH
options(warn = -1)
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_nagarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                         .combine='rbind',
                         .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_fgarch_NAGARCH)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()


# ARMA-fGARCH-TGARCH
options(warn = -1)
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_tgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                        .combine='rbind',
                        .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_fgarch_TGARCH)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()

# ARMA-fGARCH-ALLGARCH
options(warn = -1)
t1=proc.time()
cl <- makeCluster(detectCores()-1)
registerDoParallel(cl) #注册并开始并行计算
bin_arma_allgarch=foreach(i=c((garch_len+1):length(syn_future[,1])),
                          .combine='rbind',
                          .packages=c("rugarch")) %dopar% c(i,try(garch_pred_rugarch(i,spec = spec_fgarch_ALLGARCH)))
stopCluster(cl)
t2=proc.time()
t=t2-t1
writeLines(paste0(t[3][[1]],'s'))
save.image()


preds=cbind(bin_garch_f[,2],
            bin_arma_garch_f[,2],
            bin_aparch_f[,2],
            bin_arma_aparch_f[,2],
            #
            bin_arma_sgarch[,2],
            bin_arma_igarch[,2],
            bin_arma_aparch[,2],
            bin_arma_egarch[,2],
            bin_arma_gjrgarch[,2],
            bin_arma_csgarch[,2],
            #
            bin_arma_avgarch[,2],
            bin_arma_nagarch[,2],
            bin_arma_ngarch[,2],
            bin_arma_tgarch[,2],
            bin_arma_allgarch[,2]
)
preds=data.frame(preds)
for(j in 1:ncol(preds))
{
  preds[,j]=as.numeric(preds[,j])
}
any(is.na(preds))
preds[is.na(preds)]=0
any(is.na(preds))
colnames(preds)=c("garch_f","arma_garch_f","aparch_f","arma_aparch_f",
                  "arma_sGARCH_r","arma_iGARCH_r","arma_apARCH_r",
                  "arma_eGARCH_r","arma_gjrGARCH_r","arma_csGARCH_r",
                  "arma_f_avGARCH_r","arma_f_naGARCH_r","arma_f_nGARCH_r",
                  "arma_f_tGARCH_r","arma_f_allGARCH_r")

write.csv(preds,"b_all_240.csv", row.names=F, quote=F)