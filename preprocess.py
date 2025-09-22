def preprocess_dataset(df):
    df = df[df.Model != "R1-7B"].reset_index(drop=True)
    df.to_csv("./data/unlabeled_one_df_preprocessed.csv", index=False)
    return df