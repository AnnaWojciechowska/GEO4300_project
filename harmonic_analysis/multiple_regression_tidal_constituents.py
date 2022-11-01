import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from scipy import stats

def multiple_regression(df_obs, tidal_constituents, significance_level=0.05):
    """ Documentation for this function!
    
    """

    alpha = significance_level
    # Prepare for looping over the number of possible tidal constituents to 
    # include in the multiple regression

    list_of_most_important_constituents = []
    tidal_constituents_loop = tidal_constituents.copy()
    df_obs['residual'] = df_obs['level_demean'].copy()
    R2_old = 0
    results_dict = {}

    # Compute a time series of the sine and cosine of all tidal constituents
    for constituent in tidal_constituents_loop.index:
        df_cos = pd.DataFrame(
            {
                f'{constituent}_cos': np.cos(np.deg2rad(tidal_constituents.loc[constituent]['Angular Speed (degrees/hour)'].copy()*df_obs['tk'].copy()))
            }
        )

        df_sin = pd.DataFrame(
            {
                f'{constituent}_sin': np.sin(np.deg2rad(tidal_constituents.loc[constituent]['Angular Speed (degrees/hour)'].copy()*df_obs['tk'].copy()))
            }
        )
        # Add the new sine and cosine time series to the main DataFrame
        df_obs = pd.concat([df_obs, df_cos, df_sin], axis=1)

    # Do the actual loop
    for i in range(len(tidal_constituents)):
        # Initialize Pandas Series that will hold results for each iteration
        R2_values = pd.Series(dtype='object')        # Will hold the R^2 values for all linear regression models
        params_values = pd.Series(dtype='object')    # Will hold the intercept and slope of all linear regression models
        # Define some parameters needed for the F-test
        N = df_obs['residual'].count()               # Number of data points/sample size
        n = i + 1                                    # Number of used independent variables

        ###
        # Step 1: Find the most important of the remaining tidal constituents
        ###

        # Loop over all remaining constituents, fit a linear regression model and calculate the R**2 value
        for constituent in tidal_constituents_loop.index:
            # Fit linear regression model
            linfit_constituent = smf.ols(formula=f"residual ~ {constituent}_cos + {constituent}_sin", data=df_obs).fit()
            # Get the parameters from the regression
            params_values[constituent] = linfit_constituent.params
            R2_values[constituent] = linfit_constituent.rsquared
        # Check which of the remaining constituents is the most important
        most_important_constituent = R2_values.idxmax()
        print(f'Regression nr. {i+1}, most important constituent: {most_important_constituent}')

        ###
        # Step 2: Make a regression with all tidal constituents selected until now (including the new one).
        ###

        # Make a temporary copy of the list of most important constituents since the new tidal 
        # constituent might not be significant, and therefore should not be added to the global list.
        tmp_list_of_most_important_constituents = list_of_most_important_constituents.copy()
        tmp_list_of_most_important_constituents.append(most_important_constituent)

        # Make a string of the formula for the full regression model
        formula_text = "level_demean ~ "
        for constituent in tmp_list_of_most_important_constituents:
            formula_text += f'{constituent}_cos + {constituent}_sin + '
        formula_text = formula_text[:-3]    # Remove the last ' + '

        # Fit the linear regression model
        linfit_total = smf.ols(formula=formula_text, data=df_obs).fit()
        # Find R^2 for this regression
        R2_new = linfit_total.rsquared
        #print(f'  R2 full regression: {R2}')

        ###
        # Step 3: Perform a F-test to test if the new tidal constituent explain the residual variation significantly
        ###

        # Calculate the test statistics for the F-test
        F_statistic = ((1 - R2_old**2)*(N - n - 1))/((1 - R2_new**2)*(N - n - 2))
        # Find the critical value F(1-alpha, N-n-1, N-n-2)
        F_critical = stats.f.ppf(1-alpha, dfn=(N-n-1), dfd=(N-n-2))
        #print(f'  R2_old: {R2_old}')
        #print(f'  F_statistic={F_statistic:.4f}')
        #print(f'  F_critical={F_critical:.4f}')

        if F_statistic <= F_critical:
            # Not significant, terminate regression
            print(f'Adding the tidal constituent {most_important_constituent} does not significantly improve the regression. '
                  'The regression is ended here.')
            break

        ###
        # Step 4: Save the results and get ready for the next iteration
        ###

        results_dict[f'regression_{i+1}'] = {
            'most_important_constituent': most_important_constituent,
            'params' : linfit_total.params,
            'R2' : R2_new,
            'F_statistic': F_statistic,
            'F_critical': F_critical
        }

        # Store the new tidal constituent to the global list
        list_of_most_important_constituents.append(most_important_constituent)
        # Remove the new tidal constituent from the list of constituents to check in the next iteration
        tidal_constituents_loop.drop(most_important_constituent)

        # Update the residual time series by removing the regression with the new tidal constituent
        regression = (
            params_values[most_important_constituent]['Intercept']
            + params_values[most_important_constituent][f'{most_important_constituent}_cos']*df_obs[f'{most_important_constituent}_cos']
            + params_values[most_important_constituent][f'{most_important_constituent}_sin']*df_obs[f'{most_important_constituent}_sin']
        )
        df_obs['residual'] = df_obs['residual'] - regression

        # Store the R^2 value somewhere for use in the next loop (for calculating F)
        R2_old = R2_new


    # Add some results from the whole regression
    results_dict['list_of_most_important_constituents'] = list_of_most_important_constituents

    # Return the results
    return results_dict